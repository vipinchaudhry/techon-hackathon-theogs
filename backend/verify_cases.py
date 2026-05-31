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
# Actual: asked ROI, buried the camera -> bankruptcy.
# Tool should show this is an AFFORDABLE bet (low overall risk, no re-commitment
# block), i.e. keep it, not kill it.
kodak = get("Kodak")
ks = status_engine.evaluate(kodak)
check("kodak: it is a single focused project (no sub-projects)",
      db.scalar(select(Project).where(Project.parent_id == kodak.id)) is None)
check("kodak: overall risk is affordable (Low or Medium), not Critical",
      ks["overall_tier"] in ("Low", "Medium"), f"overall={ks['overall_tier']}")
check("kodak: tool does NOT demand stop / re-commitment (keep the bet)",
      ks["recommit_required"] is False)
check("kodak: tool gives a concrete next step (who to talk to)",
      bool(kodak.contact_person) and bool(kodak.smallest_test))

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
