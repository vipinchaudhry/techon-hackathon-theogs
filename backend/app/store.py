"""
Human-readable JSON mirror of the database.

SQLite is the engine (it handles the parent/child hierarchy, stakeholders, and
the audit log), but it is an opaque binary file. After every change we also write
the whole dataset to data/projects.json so the project data is visible as a plain
file you can open and watch change. GET /data serves the same snapshot.

This file is a MIRROR for transparency, not a second source of truth.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Project

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
JSON_PATH = DATA_DIR / "projects.json"

# Every project field a human would want to see / edit.
PROJECT_FIELDS = (
    "id", "name", "description", "owner", "status", "uncertainty_type",
    "parent_id",
    "money_committed", "money_spent", "time_committed_weeks", "time_spent_weeks",
    "reputation_tier", "relationships_tier", "reversibility_tier", "pnl_eur",
    "hypothesis", "smallest_test", "contact_person", "contact_question",
    "signal_keep", "signal_stop", "reevaluation_date",
    "summary",
)


def _project_dict(p: Project) -> dict:
    out = {}
    for f in PROJECT_FIELDS:
        v = getattr(p, f)
        out[f] = v.isoformat() if hasattr(v, "isoformat") else v
    out["stakeholders"] = [
        {
            "name": s.name, "role": s.role, "stake_note": s.stake_note,
            "money_tier": s.money_tier, "time_tier": s.time_tier,
            "reputation_tier": s.reputation_tier,
            "relationships_tier": s.relationships_tier,
            "reversibility_tier": s.reversibility_tier,
        }
        for s in p.stakeholders
    ]
    return out


def snapshot(db: Session) -> dict:
    """Build the full dataset as nested JSON: top-level projects with children."""
    tops = db.scalars(
        select(Project).where(Project.parent_id.is_(None)).order_by(Project.id)
    ).all()
    data = {"projects": []}
    for p in tops:
        node = _project_dict(p)
        node["sub_projects"] = [
            _project_dict(c)
            for c in db.scalars(
                select(Project).where(Project.parent_id == p.id).order_by(Project.id)
            ).all()
        ]
        data["projects"].append(node)
    return data


def export_json(db: Session) -> None:
    """Write the snapshot to data/projects.json. Safe to call after any commit."""
    DATA_DIR.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps(snapshot(db), indent=2), encoding="utf-8")
