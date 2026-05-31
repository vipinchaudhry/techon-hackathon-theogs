"""Assertion-based self-test. Prints only short PASS/FAIL tokens.

Run from the backend/ folder:
    LLM_MOCK=1 .venv/bin/python selftest.py
"""
import os
os.environ.setdefault("LLM_MOCK", "1")

from app.db import Base, engine, SessionLocal
from app import seed, status_engine, llm
from app.models import Project
from sqlalchemy import select

Base.metadata.create_all(bind=engine)
db = SessionLocal()
seed.seed_all(db, force=True)

results = []

def check(name, cond):
    results.append(f"{'PASS' if cond else 'FAIL'}:{name}")

allp = db.scalars(select(Project)).all()
tops = db.scalars(select(Project).where(Project.parent_id.is_(None))).all()
check("total10", len(allp) == 10)
check("tops3", len(tops) == 3)

kodak = db.scalar(select(Project).where(Project.name.like("Kodak%")))
google = db.scalar(select(Project).where(Project.name.like("Google%"), Project.parent_id.is_(None)))
sony = db.scalar(select(Project).where(Project.name.like("Sony%"), Project.parent_id.is_(None)))

ks = status_engine.evaluate(kodak)
check("kodak_overall_le_med", ks["overall_tier"] in ("Low", "Medium"))
check("kodak_no_recommit", ks["recommit_required"] is False)
check("kodak_has_contact", bool(kodak.contact_person))

ss = status_engine.evaluate(sony)
check("sony_overall_high", ss["overall_tier"] == "High")
check("sony_3_stake", len(sony.stakeholders) == 3)
roles = sorted(s.role for s in sony.stakeholders)
check("sony_roles", roles == ["Sponsor", "Steering", "Team"])

kids = db.scalars(select(Project).where(Project.parent_id == google.id)).all()
roll = status_engine.rollup(google, kids)
check("google_7kids", roll["child_count"] == 7)
check("google_breach", roll["boundary_breached"] is True)
check("google_flags", len(roll["portfolio_flags"]) >= 1)
check("google_sum_gt_boundary",
      roll["totals"]["money_committed"] > roll["program_boundary"]["money_committed"])

check("worst_of", status_engine._worst("Low", "High", "Medium") == "High")

parsed = llm.parse_to_fields("we have about 6 weeks and €20k, biggest risk is looking bad to the CFO")
check("parse_money", parsed.get("money_committed") == 20000)
check("parse_time", parsed.get("time_committed_weeks") == 6)
check("parse_rep", parsed.get("reputation_tier") == "High")

d1 = llm.detect_drift("what ROI will this get us, the upside could be huge")
d2 = llm.detect_drift("what can we absorb if this fails")
check("drift_true", d1["drift"] is True)
check("drift_false", d2["drift"] is False)

db.close()

n_fail = sum(1 for r in results if r.startswith("FAIL"))
print("SUMMARY", len(results), "checks", n_fail, "failed")
for r in results:
    if r.startswith("FAIL"):
        print(r)
print("DONE_OK" if n_fail == 0 else "DONE_FAIL")
