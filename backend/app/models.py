"""
Database tables.

Core idea (from the challenge): a project carries an Affordable-Loss profile across
5 dimensions. Two of them are numeric (money, time) and three are qualitative tiers
(reputation, relationships, reversibility). Projects can nest (parent -> sub-projects)
so a program's loss can be rolled up. Stakeholders each carry their OWN loss profile
(the Sony case). Every change is written to an audit log (no silent continuation).
"""

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Allowed values kept as plain tuples so they're easy to read and validate.
TIERS = ("Low", "Medium", "High", "Critical")
STATUSES = ("Active", "Paused", "Stopped", "Complete")
UNCERTAINTY_TYPES = ("Technology", "Market", "Stakeholder", "Resource")
STAKEHOLDER_ROLES = ("Team", "Sponsor", "Steering")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="Active")
    uncertainty_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Self-referential hierarchy: a project may have a parent program.
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    children: Mapped[list["Project"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped["Project | None"] = relationship(
        back_populates="children", remote_side="Project.id"
    )

    # --- Affordable Loss: numeric dimensions (committed vs consumed) ---
    money_committed: Mapped[float] = mapped_column(Float, default=0.0)
    money_spent: Mapped[float] = mapped_column(Float, default=0.0)
    time_committed_weeks: Mapped[float] = mapped_column(Float, default=0.0)
    time_spent_weeks: Mapped[float] = mapped_column(Float, default=0.0)

    # --- Affordable Loss: qualitative tier dimensions ---
    reputation_tier: Mapped[str] = mapped_column(String(10), default="Low")
    relationships_tier: Mapped[str] = mapped_column(String(10), default="Low")
    reversibility_tier: Mapped[str] = mapped_column(String(10), default="Low")

    # --- Guardrail / escalation (the Slack bot) ---
    # Where the project lives in Slack, who to escalate to, and how far up the
    # escalation ladder we have climbed (0 = fine, higher = more insistent).
    slack_channel: Mapped[str] = mapped_column(String(80), default="")
    sponsor: Mapped[str] = mapped_column(String(120), default="")
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    frozen: Mapped[bool] = mapped_column(Integer, default=0)  # 0/1 stored as int

    # --- Profit / loss forecast ---
    # positive = green (profit), negative = red (loss), NULL = grey (no forecast yet)
    pnl_eur: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    # --- The concrete next step (challenge problem #3) ---
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    smallest_test: Mapped[str] = mapped_column(Text, default="")
    contact_person: Mapped[str] = mapped_column(String(200), default="")
    contact_question: Mapped[str] = mapped_column(Text, default="")
    signal_keep: Mapped[str] = mapped_column(Text, default="")
    signal_stop: Mapped[str] = mapped_column(Text, default="")
    reevaluation_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # When the team last made an explicit continue/stop decision.
    last_decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Hand-me-down: a short summary the LLM leaves for its next run ---
    # Future check-ins read this instead of re-analysing the whole project,
    # which saves tokens. Empty until the first opinion is generated.
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    stakeholders: Mapped[list["Stakeholder"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list["AuditLog"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AuditLog.timestamp.desc()",
    )


class Stakeholder(Base):
    """A person/role with their OWN loss profile on a project (Sony case)."""

    __tablename__ = "stakeholders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project: Mapped["Project"] = relationship(back_populates="stakeholders")

    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="Team")  # Team/Sponsor/Steering
    stake_note: Mapped[str] = mapped_column(Text, default="")  # what they have at risk

    # Each stakeholder sees the 5 dimensions through their own eyes.
    money_tier: Mapped[str] = mapped_column(String(10), default="Low")
    time_tier: Mapped[str] = mapped_column(String(10), default="Low")
    reputation_tier: Mapped[str] = mapped_column(String(10), default="Low")
    relationships_tier: Mapped[str] = mapped_column(String(10), default="Low")
    reversibility_tier: Mapped[str] = mapped_column(String(10), default="Low")


class AuditLog(Base):
    """Every change, especially continue/stop decisions. No silent continuation."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project: Mapped["Project"] = relationship(back_populates="audit_entries")

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text, default="")


class ChatMessage(Base):
    """A persisted message in the 'Ask about this portfolio' conversation.

    Stored per project so the history survives refreshes, navigation, and restarts.
    role is 'user' or 'bot'.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    role: Mapped[str] = mapped_column(String(10))  # "user" | "bot"
    text: Mapped[str] = mapped_column(Text, default="")
