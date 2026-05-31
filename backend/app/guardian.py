"""
The guardrail: the persistent-escalation engine behind the Slack bot.

Pure logic, no Slack imports, so it can be tested on its own. The Slack layer
(slackbot.py) just calls these functions and posts whatever text they return.

Core idea: when a project crosses its affordable-loss boundary and nobody has
logged an explicit keep/stop decision, the guardian climbs an escalation ladder.
Each step is more insistent. If still ignored, the safe default acts: it FREEZES
the project. Drifting stops being the path of least resistance.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import status_engine
from .models import AuditLog, Project


def _eur(n: float) -> str:
    n = int(round(n or 0))
    return f"€{n/1000:.0f}k" if abs(n) >= 1000 else f"€{n}"


def consumed_ratio(p: Project) -> float:
    """Highest consumed-vs-committed ratio across money and time (0..>1)."""
    ratios = []
    if p.money_committed:
        ratios.append(p.money_spent / p.money_committed)
    if p.time_committed_weeks:
        ratios.append(p.time_spent_weeks / p.time_committed_weeks)
    return max(ratios) if ratios else 0.0


def over_boundary(p: Project) -> bool:
    """True once spend or time has reached 80% of the affordable-loss boundary."""
    return consumed_ratio(p) >= 0.8


# The ladder. Level -> (label, how to build the message). Level 4 freezes.
LADDER = {
    1: "nudge",
    2: "warn",
    3: "sponsor",
    4: "freeze",
}


def profile_text(p: Project) -> str:
    """The affordable-loss snapshot, plain text for Slack."""
    pct_money = int(100 * (p.money_spent / p.money_committed)) if p.money_committed else 0
    pct_time = int(100 * (p.time_spent_weeks / p.time_committed_weeks)) if p.time_committed_weeks else 0
    return (
        f"*{p.name}* — what you can afford to lose:\n"
        f"• Money: {_eur(p.money_spent)} of {_eur(p.money_committed)} ({pct_money}%)\n"
        f"• Time: {p.time_spent_weeks:g} of {p.time_committed_weeks:g} weeks ({pct_time}%)\n"
        f"• Reputation: {p.reputation_tier}"
    )


def next_step_text(p: Project) -> str:
    bits = []
    if p.contact_person:
        bits.append(f"Talk to {p.contact_person}.")
    if p.contact_question:
        bits.append(f"Ask: {p.contact_question}")
    if p.signal_keep:
        bits.append(f"Keep going if {p.signal_keep}")
    if p.signal_stop:
        bits.append(f"Stop if {p.signal_stop}")
    return " ".join(bits) or "Define the smallest test and who to talk to this week."


def _log(db: Session, p: Project, action: str, detail: str, actor: str = "guardian"):
    p.audit_entries.append(AuditLog(actor=actor, action=action, detail=detail))


def log_decision(db: Session, p: Project, decision: str, actor: str = "team", note: str = "") -> str:
    """Record an explicit keep / stop / resume decision. Resets escalation."""
    decision = decision.strip().lower()
    p.last_decision_at = datetime.now(timezone.utc)
    p.escalation_level = 0
    if decision == "stop":
        p.status = "Stopped"
        p.frozen = 0
        msg = f"Logged: *stop* by {actor}. {note}".strip()
    elif decision == "resume":
        p.status = "Active"
        p.frozen = 0
        msg = (f"Logged: *resume* by {actor}. Budget unfrozen. "
               "The clock is running again, so watch the boundary.")
    else:  # keep / continue
        p.status = "Active"
        p.frozen = 0
        msg = f"Logged: *keep going* by {actor}. {note}".strip()
        msg += "\nThis is now a conscious bet. If it fails, it fails on purpose."
    _log(db, p, f"decision:{decision}", note or f"{decision} by {actor}", actor=actor)
    db.commit()
    return msg


def advance_time(db: Session, p: Project, weeks: float = 2.0, money: float | None = None) -> None:
    """Demo control: simulate time/spend passing so the boundary gets crossed.

    Money defaults to a proportional burn if not given.
    """
    p.time_spent_weeks = (p.time_spent_weeks or 0) + weeks
    if money is None and p.time_committed_weeks:
        # burn money at the committed rate
        rate = p.money_committed / p.time_committed_weeks if p.time_committed_weeks else 0
        money = rate * weeks
    p.money_spent = (p.money_spent or 0) + (money or 0)
    _log(db, p, "time-advanced", f"+{weeks:g} weeks, +{_eur(money or 0)} spent")
    db.commit()


def check(db: Session, p: Project) -> dict:
    """The heartbeat. Decide whether to escalate and return what (if anything)
    the bot should post. Call this after time advances or on a schedule.

    Returns {"posted": bool, "level": int, "frozen": bool, "message": str}.
    """
    # If the team already made a decision and we are within boundary, stay quiet.
    if not over_boundary(p) or p.status == "Stopped":
        return {"posted": False, "level": p.escalation_level, "frozen": bool(p.frozen), "message": ""}

    pct = int(100 * consumed_ratio(p))

    # Already frozen: keep reminding, do not climb further.
    if p.frozen:
        return {
            "posted": False, "level": p.escalation_level, "frozen": True,
            "message": "",
        }

    # Climb one rung.
    p.escalation_level = min(p.escalation_level + 1, 4)
    level = p.escalation_level
    name = p.name

    if level == 1:
        msg = (
            f"⏰ *{name}* just crossed its affordable-loss boundary "
            f"({pct}% consumed). No keep/stop decision is on record.\n"
            f"Reply *keep* or *stop* so the team decides on purpose."
        )
    elif level == 2:
        who = f" <@{p.owner}>" if p.owner else ""
        msg = (
            f"⚠️ Still no decision on *{name}*.{who} Every day with no call, it is "
            f"drifting on autopilot at {pct}% of what you can afford to lose.\n"
            f"Reply *keep* or *stop*."
        )
    elif level == 3:
        sponsor = p.sponsor or "the sponsor"
        msg = (
            f"📩 *{name}* has been past its boundary with no decision. "
            f"I'm escalating to {sponsor}. Last chance to decide before I freeze the "
            f"budget: reply *keep* or *stop*."
        )
    else:  # level 4 -> FREEZE
        p.frozen = 1
        p.status = "Frozen"
        msg = (
            f"🧊 *{name} is frozen.* {_eur(p.money_spent)} of {_eur(p.money_committed)} "
            f"was committed with no logged decision, so I stopped the spend by default.\n"
            f"Nothing more goes in until a human decides: reply *resume* to keep going "
            f"(with a reason) or *stop* to close it out."
        )
        _log(db, p, "frozen", f"auto-frozen at {pct}% consumed, no decision")

    db.commit()
    return {"posted": True, "level": level, "frozen": bool(p.frozen), "message": msg}
