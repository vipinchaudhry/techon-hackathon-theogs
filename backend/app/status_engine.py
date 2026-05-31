"""
The "black box" status engine. HYBRID:

  - Deterministic RULES decide the objective things:
        * money/time risk from consumed-vs-committed ratios
        * whether a re-evaluation is overdue
        * portfolio rollup (sum numeric, worst-of tiers)
        * whether an explicit re-commitment is required
  - The LLM (or its mock) decides the FUZZY things:
        * drift from Affordable-Loss language toward expected-return language

It outputs signals the UI consumes. It never makes the stop/go decision for the team.
"""

from datetime import date, datetime, timezone

from . import llm
from .models import Project

# Tier ordering so we can compare / take the worst.
TIER_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
ORDER_TIER = {v: k for k, v in TIER_ORDER.items()}

# Numeric risk -> tier, from consumed/committed ratio.
def _ratio_to_tier(spent: float, committed: float) -> tuple[str, float | None]:
    if committed <= 0:
        return "Low", None
    ratio = spent / committed
    if ratio >= 1.0:
        return "Critical", ratio
    if ratio >= 0.8:
        return "High", ratio
    if ratio >= 0.5:
        return "Medium", ratio
    return "Low", ratio


def _worst(*tiers: str) -> str:
    best = max((TIER_ORDER.get(t, 1) for t in tiers), default=1)
    return ORDER_TIER[best]


def per_dimension_risk(p: Project) -> dict:
    """Risk tier for each of the 5 dimensions for one project."""
    money_tier, money_ratio = _ratio_to_tier(p.money_spent, p.money_committed)
    time_tier, time_ratio = _ratio_to_tier(p.time_spent_weeks, p.time_committed_weeks)
    return {
        "money": {
            "tier": money_tier,
            "committed": p.money_committed,
            "spent": p.money_spent,
            "ratio": None if money_ratio is None else round(money_ratio, 2),
        },
        "time": {
            "tier": time_tier,
            "committed": p.time_committed_weeks,
            "spent": p.time_spent_weeks,
            "ratio": None if time_ratio is None else round(time_ratio, 2),
        },
        "reputation": {"tier": p.reputation_tier},
        "relationships": {"tier": p.relationships_tier},
        "reversibility": {"tier": p.reversibility_tier},
    }


def overall_tier(p: Project) -> str:
    dims = per_dimension_risk(p)
    return _worst(
        dims["money"]["tier"],
        dims["time"]["tier"],
        dims["reputation"]["tier"],
        dims["relationships"]["tier"],
        dims["reversibility"]["tier"],
    )


def _days_to_reeval(p: Project) -> int | None:
    if not p.reevaluation_date:
        return None
    today = datetime.now(timezone.utc).date()
    return (p.reevaluation_date - today).days


def evaluate(p: Project) -> dict:
    """Full status for a single project."""
    dims = per_dimension_risk(p)
    overall = overall_tier(p)
    days = _days_to_reeval(p)

    reasons: list[str] = []

    # --- re-commitment rules ---
    recommit = False
    if days is not None and days <= 0:
        recommit = True
        reasons.append(
            f"Re-evaluation date passed {abs(days)} day(s) ago with no logged decision."
            if days < 0
            else "Re-evaluation date is today."
        )
    if dims["money"]["ratio"] is not None and dims["money"]["ratio"] >= 0.8:
        recommit = True
        reasons.append(
            f"Money consumed is {int(dims['money']['ratio'] * 100)}% of the affordable boundary."
        )
    if dims["time"]["ratio"] is not None and dims["time"]["ratio"] >= 0.8:
        recommit = True
        reasons.append(
            f"Time consumed is {int(dims['time']['ratio'] * 100)}% of the affordable boundary."
        )
    if overall == "Critical":
        recommit = True
        reasons.append("Overall affordable-loss boundary is at Critical.")

    # --- drift (LLM / mock) ---
    drift_text = " ".join(
        t for t in [p.description, p.hypothesis, p.signal_keep] if t
    ).strip()
    drift = (
        llm.detect_drift(drift_text)
        if drift_text
        else {"drift": False, "reason": "Not enough text to assess."}
    )

    # --- recommended action (a suggestion, never a decision) ---
    if recommit:
        action = (
            "Stop and make an explicit continue/stop decision before any more work. "
            + reasons[0]
        )
    elif overall in ("High", "Critical"):
        action = "Review the loss profile with the sponsor this week; you're near a boundary."
    elif not p.contact_person or not p.smallest_test:
        action = "Define the smallest test and the specific person to talk to this week."
    else:
        action = f"Proceed with the smallest test: contact {p.contact_person}."

    return {
        "project_id": p.id,
        "overall_tier": overall,
        "dimensions": dims,
        "days_to_reevaluation": days,
        "recommit_required": recommit,
        "recommit_reasons": reasons,
        "drift_flag": bool(drift.get("drift")),
        "drift_reason": drift.get("reason", ""),
        "recommended_action": action,
        "uncertainty_type": p.uncertainty_type,
    }


# --- portfolio rollup (the Google case) ---------------------------------------

def rollup(parent: Project, children: list[Project]) -> dict:
    """
    Roll sub-projects up to the program level.
      - money/time: SUM of children's committed and spent
      - tiers: WORST-OF across children (you cannot average reputation)
    The parent's own committed numbers act as the PROGRAM boundary; if the sum of
    children's commitments exceeds it, that's the silent-erosion signal.
    """
    total_money_committed = sum(c.money_committed for c in children)
    total_money_spent = sum(c.money_spent for c in children)
    total_time_committed = sum(c.time_committed_weeks for c in children)
    total_time_spent = sum(c.time_spent_weeks for c in children)

    worst_reputation = _worst(*(c.reputation_tier for c in children)) if children else "Low"
    worst_relationships = _worst(*(c.relationships_tier for c in children)) if children else "Low"
    worst_reversibility = _worst(*(c.reversibility_tier for c in children)) if children else "Low"

    money_over = (
        parent.money_committed > 0 and total_money_committed > parent.money_committed
    )
    time_over = (
        parent.time_committed_weeks > 0
        and total_time_committed > parent.time_committed_weeks
    )

    active = [c for c in children if c.status == "Active"]

    flags: list[str] = []
    if money_over:
        flags.append(
            f"Sub-project commitments (€{int(total_money_committed):,}) exceed the program's "
            f"affordable-loss boundary (€{int(parent.money_committed):,})."
        )
    if time_over:
        flags.append(
            f"Sub-project time commitments ({total_time_committed:g} wks) exceed the "
            f"program boundary ({parent.time_committed_weeks:g} wks)."
        )
    if len(active) >= 8:
        flags.append(
            f"{len(active)} active sub-projects — no single one looks dangerous, but the "
            "program as a whole may be bleeding out."
        )

    return {
        "parent_id": parent.id,
        "child_count": len(children),
        "active_child_count": len(active),
        "totals": {
            "money_committed": total_money_committed,
            "money_spent": total_money_spent,
            "time_committed_weeks": total_time_committed,
            "time_spent_weeks": total_time_spent,
        },
        "program_boundary": {
            "money_committed": parent.money_committed,
            "time_committed_weeks": parent.time_committed_weeks,
        },
        "worst_tiers": {
            "reputation": worst_reputation,
            "relationships": worst_relationships,
            "reversibility": worst_reversibility,
        },
        "boundary_breached": money_over or time_over,
        "portfolio_flags": flags,
    }
