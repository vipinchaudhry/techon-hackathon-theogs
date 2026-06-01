"""Pydantic request/response models (the API's public shapes)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StakeholderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    role: str
    stake_note: str
    money_tier: str
    time_tier: str
    reputation_tier: str
    relationships_tier: str
    reversibility_tier: str


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime
    actor: str
    action: str
    detail: str


class ProjectBase(BaseModel):
    name: str
    description: str = ""
    owner: str = ""
    status: str = "Active"
    uncertainty_type: str | None = None
    parent_id: int | None = None

    money_committed: float = 0.0
    money_spent: float = 0.0
    time_committed_weeks: float = 0.0
    time_spent_weeks: float = 0.0

    reputation_tier: str = "Low"
    relationships_tier: str = "Low"
    reversibility_tier: str = "Low"

    pnl_eur: float | None = None

    hypothesis: str = ""
    smallest_test: str = ""
    contact_person: str = ""
    contact_question: str = ""
    signal_keep: str = ""
    signal_stop: str = ""
    reevaluation_date: date | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    """All optional: patch only the fields you send."""

    name: str | None = None
    description: str | None = None
    owner: str | None = None
    status: str | None = None
    uncertainty_type: str | None = None
    parent_id: int | None = None
    money_committed: float | None = None
    money_spent: float | None = None
    time_committed_weeks: float | None = None
    time_spent_weeks: float | None = None
    reputation_tier: str | None = None
    relationships_tier: str | None = None
    reversibility_tier: str | None = None
    pnl_eur: float | None = None
    hypothesis: str | None = None
    smallest_test: str | None = None
    contact_person: str | None = None
    contact_question: str | None = None
    signal_keep: str | None = None
    signal_stop: str | None = None
    reevaluation_date: date | None = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    last_decision_at: datetime | None = None
    stakeholders: list[StakeholderOut] = []


class ChatIn(BaseModel):
    message: str
    project_id: int | None = None  # context, if the chat is about a specific project


class DecisionIn(BaseModel):
    decision: str  # "continue" or "stop"
    actor: str = "team"
    note: str = ""


class AnalyzeIn(BaseModel):
    idea: str
    history: list[str] = []


class ConsultIn(BaseModel):
    question: str
    project_id: int | None = None  # optional: anchor the consult to one project


class CheckInIn(BaseModel):
    progress: str = ""  # the user's progress update at the check-in


class AdoptIn(BaseModel):
    decision: str = "no"          # "yes" | "no"
    name: str = ""                # project name if adopting
    budget_eur: float | None = None
    reason: str = ""              # why not, if declining


class AddNodeIn(BaseModel):
    parent_id: int
    name: str
    money_committed: float = 0.0
    description: str = ""
    uncertainty_type: str | None = None
    # carry the analyzer's dimension tiers if we have them
    reputation_tier: str = "Low"
    relationships_tier: str = "Low"
    reversibility_tier: str = "Low"
