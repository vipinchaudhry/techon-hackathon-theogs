"""
Acceptance test for the hackathon question: "would this tool have changed the
outcome?" for all three case studies.

For each case we feed the seeded data through the REAL tool logic (status engine
+ rollup + stakeholder model) and assert the tool produces the affordable-loss
signal that contradicts the decision the company actually made.

Run from the backend/ folder (no API key needed, runs the deterministic engine):
    LLM_MOCK=1 .venv/bin/python verify_cases.py
"""
import os
os.environ.setdefault("LLM_MOCK", "1")  # engine assertions do not need the LLM

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app import seed, status_engine
from app.models import Project

Base.metadata.create_all(bind=engine)
db = SessionLocal()
seed.seed_all(db, force=True)

results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

def get(name_like):
    return db.scalar(select(Project).where(Project.name.like(name_like + "%"),
                                           Project.parent_id.is_(None)))

# ---------------------------------------------------------------- KODAK --------
# Actual: judged each project on ROI, the digital bets lose money -> buried them
# -> bankruptcy. Seen as a PORTFOLIO, the red digital bets are small and
# affordable next to the green film profits, so they are bets to keep.
kodak = get("Kodak")
kodak_teams = list(db.scalars(select(Project).where(Project.parent_id == kodak.id)).all())
kodak_kids = []
for t in kodak_teams:
    kodak_kids += list(db.scalars(select(Project).where(Project.parent_id == t.id)).all())
check("kodak: organised into teams", len(kodak_teams) >= 3, f"teams={len(kodak_teams)}")
check("kodak: teams own the individual project bets", len(kodak_kids) >= 8,
      f"projects={len(kodak_kids)}")
greens = [c for c in kodak_kids if (c.pnl_eur or 0) > 0]
reds = [c for c in kodak_kids if (c.pnl_eur or 0) < 0]
check("kodak: has both money-makers and money-losers",
      len(greens) > 0 and len(reds) > 0, f"green={len(greens)} red={len(reds)}")
check("kodak: green profits dwarf the red losses (the losses are affordable)",
      sum(c.pnl_eur for c in greens) > abs(sum(c.pnl_eur for c in reds)),
      f"green=+{int(sum(c.pnl_eur for c in greens)):,} red={int(sum(c.pnl_eur for c in reds)):,}")
check("kodak: each red digital bet alone is survivable, not Critical",
      all(status_engine.overall_tier(c) != "Critical" for c in reds))

# --------------------------------------------------------------- GOOGLE --------
# Actual: no single project looked bad -> silent erosion -> program died.
# Tool should fire a PROGRAM-LEVEL boundary breach across the portfolio.
google = get("Google")
kids = list(db.scalars(select(Project).where(Project.parent_id == google.id)).all())
roll = status_engine.rollup(google, kids)
check("google: has multiple sub-projects", len(kids) >= 3, f"n={len(kids)}")
check("google: each sub-project alone looks survivable",
      all(status_engine.overall_tier(c) != "Critical" for c in kids))
check("google: rolled up, the program boundary IS breached",
      roll["boundary_breached"] is True)
check("google: tool surfaces at least one portfolio warning",
      len(roll["portfolio_flags"]) >= 1,
      roll["portfolio_flags"][0] if roll["portfolio_flags"] else "")

# ---------------------------------------------------------------- SONY ---------
# Actual: room nearly killed it judging by one shared view.
# Tool should show stakeholders have DIFFERENT affordable-loss profiles, and the
# sponsor can absorb more than the team.
sony = get("Sony")
shs = {s.role: s for s in sony.stakeholders}
team = shs.get("Team")
sponsor = shs.get("Sponsor")
def tier_val(t):
    return status_engine.TIER_ORDER[status_engine._worst(
        t.money_tier, t.time_tier, t.reputation_tier, t.relationships_tier, t.reversibility_tier)]
check("sony: has multiple stakeholders", len(sony.stakeholders) >= 2)
check("sony: team and sponsor exist", team is not None and sponsor is not None)
check("sony: their overall profiles actually differ (not one shared number)",
      team and sponsor and tier_val(team) != tier_val(sponsor),
      f"team={tier_val(team)} sponsor={tier_val(sponsor)}")
check("sony: on money, the sponsor can absorb more than the team",
      team and sponsor and
      status_engine.TIER_ORDER[sponsor.money_tier] > status_engine.TIER_ORDER[team.money_tier],
      f"team.money={team.money_tier} sponsor.money={sponsor.money_tier}")

db.close()

# ---------------------------------------------------------------- report -------
passed = sum(1 for _, ok, _ in results if ok)
print(f"\nWOULD IT HAVE CHANGED THE OUTCOME?  {passed}/{len(results)} checks passed\n")
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    line = f"  [{mark}] {name}"
    if detail:
        line += f"   ({detail})"
    print(line)
print()
print("DONE_OK" if passed == len(results) else "DONE_FAIL")
raise SystemExit(0 if passed == len(results) else 1)
