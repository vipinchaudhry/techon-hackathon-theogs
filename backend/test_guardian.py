"""Prove the escalation ladder works end to end, no Slack needed.

Run from backend/:  LLM_MOCK=1 .venv/bin/python test_guardian.py
"""
import os
os.environ.setdefault("LLM_MOCK", "1")

from datetime import date, timedelta

from app.db import Base, SessionLocal, engine
from app import guardian
from app.models import Project

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Fresh demo project with a small affordable-loss boundary.
for p in db.query(Project).all():
    db.delete(p)
db.commit()

p = Project(
    name="AI Support Pilot",
    owner="maya",
    sponsor="the COO",
    status="Active",
    money_committed=15000, money_spent=2000,
    time_committed_weeks=8, time_spent_weeks=1,
    reputation_tier="Medium",
    contact_person="3 support agents",
    contact_question="would you want this again?",
    signal_keep="agents reuse it",
    signal_stop="it makes more cleanup than it saves",
)
db.add(p)
db.commit()

print("KICKOFF")
print(guardian.profile_text(p))
print("Next step:", guardian.next_step_text(p))
print(f"over_boundary={guardian.over_boundary(p)}  (expect False)\n")

print("=== simulate time passing, watch the ladder climb ===")
for i in range(6):
    guardian.advance_time(db, p, weeks=2)
    r = guardian.check(db, p)
    pct = int(100 * guardian.consumed_ratio(p))
    if r["posted"]:
        print(f"[tick {i+1}] consumed={pct}% level={r['level']} frozen={r['frozen']}")
        print("   BOT:", r["message"].replace("\n", "\n        "))
    else:
        print(f"[tick {i+1}] consumed={pct}% (quiet, level={r['level']} frozen={r['frozen']})")
    if r["frozen"]:
        break

print(f"\nstatus now: {p.status}  (expect Frozen)")

print("\n=== team finally decides: resume ===")
print("BOT:", guardian.log_decision(db, p, "resume", actor="maya", note="agents love it"))
print(f"status={p.status} frozen={bool(p.frozen)} escalation_level={p.escalation_level}  (expect Active / False / 0)")

# Verify it would re-escalate again if ignored after resume
guardian.advance_time(db, p, weeks=2)
r = guardian.check(db, p)
print(f"\nafter resume + more drift: posted={r['posted']} level={r['level']}  (expect it climbs again)")

ok = (p.status == "Active")
db.close()
print("\nDONE_OK" if ok else "\nDONE_FAIL")
