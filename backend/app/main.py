"""
FastAPI app: the Uncertainty Navigator backend.

Run from the backend/ folder:
    uvicorn app.main:app --reload --port 8000

Interactive API docs: http://localhost:8000/docs
"""

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config, llm, schemas, seed, status_engine, store
from .db import Base, SessionLocal, engine, get_db
from .models import AuditLog, ChatMessage, Project

# Project fields the navigator (or a manual edit) may change.
EDITABLE_FIELDS = (
    "money_committed", "money_spent", "time_committed_weeks", "time_spent_weeks",
    "reputation_tier", "relationships_tier", "reversibility_tier",
    "uncertainty_type", "pnl_eur",
)

app = FastAPI(title="Uncertainty Navigator", version="1.0")

# Allow the Next.js dev server (and anything local) to call us. Wide-open is fine
# for a local hackathon demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed.seed_all(db)  # only seeds if empty
        store.export_json(db)  # write the readable JSON mirror
    finally:
        db.close()


def _get_project(db: Session, project_id: int) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, f"Project {project_id} not found")
    return p


# --- meta ----------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        **config.status_summary(),
        "llm_spent_usd": llm.spent_usd(),
    }


@app.post("/reset")
def reset(db: Session = Depends(get_db)) -> dict:
    """Wipe and re-seed the three case studies. Handy between demo runs."""
    seed.seed_all(db, force=True)
    store.export_json(db)
    return {"ok": True, "message": "Re-seeded Kodak, Google, Sony."}


@app.get("/data")
def data(db: Session = Depends(get_db)) -> dict:
    """The whole dataset as plain JSON (same content as data/projects.json)."""
    return store.snapshot(db)


# --- projects ------------------------------------------------------------------

@app.get("/projects", response_model=list[schemas.ProjectOut])
def list_projects(
    top_level_only: bool = False, db: Session = Depends(get_db)
) -> list[Project]:
    stmt = select(Project)
    if top_level_only:
        stmt = stmt.where(Project.parent_id.is_(None))
    return list(db.scalars(stmt.order_by(Project.id)).all())


@app.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    return _get_project(db, project_id)


@app.get("/projects/{project_id}/children", response_model=list[schemas.ProjectOut])
def get_children(project_id: int, db: Session = Depends(get_db)) -> list[Project]:
    _get_project(db, project_id)
    return list(
        db.scalars(
            select(Project).where(Project.parent_id == project_id).order_by(Project.id)
        ).all()
    )


@app.post("/projects", response_model=schemas.ProjectOut, status_code=201)
def create_project(body: schemas.ProjectCreate, db: Session = Depends(get_db)) -> Project:
    p = Project(**body.model_dump())
    db.add(p)
    db.flush()
    p.audit_entries.append(AuditLog(actor="user", action="created", detail=p.name))
    db.commit()
    store.export_json(db)
    return p


@app.patch("/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int, body: schemas.ProjectUpdate, db: Session = Depends(get_db)
) -> Project:
    p = _get_project(db, project_id)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(p, field, value)
    if changes:
        p.audit_entries.append(
            AuditLog(
                actor="user",
                action="updated",
                detail=", ".join(f"{k}={v}" for k, v in changes.items())[:480],
            )
        )
    db.commit()
    store.export_json(db)
    return p


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict:
    p = _get_project(db, project_id)
    db.delete(p)
    db.commit()
    store.export_json(db)
    return {"ok": True}


# --- status engine -------------------------------------------------------------

@app.get("/projects/{project_id}/status")
def project_status(project_id: int, db: Session = Depends(get_db)) -> dict:
    p = _get_project(db, project_id)
    return status_engine.evaluate(p)


@app.get("/projects/{project_id}/rollup")
def project_rollup(project_id: int, db: Session = Depends(get_db)) -> dict:
    parent = _get_project(db, project_id)
    children = list(
        db.scalars(select(Project).where(Project.parent_id == project_id)).all()
    )
    return status_engine.rollup(parent, children)


@app.get("/projects/{project_id}/graph")
def project_graph(project_id: int, db: Session = Depends(get_db)) -> dict:
    """Nodes + links for an Obsidian-style portfolio graph.

    The parent is the centre node; each sub-project is a node coloured by
    profit (green) or loss (red), sized by money committed.
    """
    parent = _get_project(db, project_id)
    children = list(
        db.scalars(select(Project).where(Project.parent_id == project_id)).all()
    )

    def state_of(p: Project) -> str:
        if p.pnl_eur is None:
            return "neutral"
        return "profit" if p.pnl_eur >= 0 else "loss"

    def node(p: Project, is_center: bool):
        return {
            "id": p.id,
            "name": p.name,
            "pnl_eur": p.pnl_eur,
            "state": "center" if is_center else state_of(p),
            "money_committed": p.money_committed,
            "overall_tier": status_engine.overall_tier(p),
            "is_center": is_center,
        }

    nodes = [node(parent, True)] + [node(c, False) for c in children]
    links = [{"source": parent.id, "target": c.id} for c in children]
    total_pnl = sum(c.pnl_eur for c in children if c.pnl_eur is not None)
    return {
        "center_id": parent.id,
        "nodes": nodes,
        "links": links,
        "totals": {
            "pnl_eur": total_pnl,
            "profit_count": sum(1 for c in children if c.pnl_eur is not None and c.pnl_eur >= 0),
            "loss_count": sum(1 for c in children if c.pnl_eur is not None and c.pnl_eur < 0),
            "neutral_count": sum(1 for c in children if c.pnl_eur is None),
            "node_count": len(children),
        },
    }


# --- stakeholders / act-as (Sony) ---------------------------------------------

@app.get("/projects/{project_id}/stakeholders", response_model=list[schemas.StakeholderOut])
def list_stakeholders(project_id: int, db: Session = Depends(get_db)):
    p = _get_project(db, project_id)
    return p.stakeholders


@app.get("/projects/{project_id}/as/{stakeholder_id}")
def view_as_stakeholder(
    project_id: int, stakeholder_id: int, db: Session = Depends(get_db)
) -> dict:
    """The same project seen through one stakeholder's loss profile."""
    p = _get_project(db, project_id)
    sh = next((s for s in p.stakeholders if s.id == stakeholder_id), None)
    if not sh:
        raise HTTPException(404, "Stakeholder not found on this project")
    tiers = {
        "money": sh.money_tier,
        "time": sh.time_tier,
        "reputation": sh.reputation_tier,
        "relationships": sh.relationships_tier,
        "reversibility": sh.reversibility_tier,
    }
    worst = status_engine._worst(*tiers.values())
    # A short, stakeholder-specific framing line.
    if sh.role == "Team":
        framing = (
            f"You ({sh.name}) are already over-committed — your reputation and time are "
            "the binding constraints. This decision is barely reversible for you."
        )
    elif sh.role == "Sponsor":
        framing = (
            f"You ({sh.name}) can absorb losses the team cannot. Because your affordable "
            "loss is larger, the continue/stop call should sit with you, not them."
        )
    else:
        framing = (
            f"You ({sh.name}) carry reputational and relationship exposure. Make sure "
            "the team's bet isn't quietly becoming your liability."
        )
    return {
        "stakeholder": schemas.StakeholderOut.model_validate(sh).model_dump(),
        "tiers": tiers,
        "overall_tier": worst,
        "framing": framing,
    }


# --- chat / natural-language parsing -------------------------------------------

@app.post("/chat")
def chat(body: schemas.ChatIn, db: Session = Depends(get_db)) -> dict:
    """
    Parse natural language into structured loss fields and check for drift.
    If project_id is given, the parsed numeric/tier fields are applied to it.
    """
    # Give the parser the project's current values so relative edits
    # ("budget went down by 20k") resolve against them.
    current = None
    p = None
    if body.project_id is not None:
        p = _get_project(db, body.project_id)
        current = {f: getattr(p, f) for f in EDITABLE_FIELDS}

    parsed = llm.parse_to_fields(body.message, current)
    drift = llm.detect_drift(body.message)

    applied = {}
    if p is not None:
        for field in EDITABLE_FIELDS:
            if field in parsed and parsed[field] is not None:
                setattr(p, field, parsed[field])
                applied[field] = parsed[field]
        if applied:
            p.audit_entries.append(
                AuditLog(
                    actor="navigator",
                    action="edited-from-chat",
                    detail=", ".join(f"{k}={v}" for k, v in applied.items())[:480],
                )
            )
            db.commit()
            store.export_json(db)  # keep the readable JSON mirror in sync

    return {
        "assistant_reply": parsed.get("assistant_reply", ""),
        "clarifying_questions": parsed.get("clarifying_questions", []),
        "parsed_fields": parsed,
        "applied_fields": applied,
        "drift": drift,
        "mock_mode": config.LLM_MOCK,
    }


def _portfolio_context(parent: Project, children: list[Project]) -> str:
    """A short text snapshot of a portfolio the LLM can reason over."""
    lines = [f"Program: {parent.name}. {parent.description}"]
    for c in children:
        state = "PROFIT" if c.pnl_eur >= 0 else "LOSS"
        lines.append(
            f"- {c.name}: {state} EUR {int(c.pnl_eur):,}; "
            f"committed EUR {int(c.money_committed):,}, spent EUR {int(c.money_spent):,}; "
            f"reputation {c.reputation_tier}; uncertainty {c.uncertainty_type}; "
            f"status {c.status}."
        )
    total = sum(c.pnl_eur for c in children)
    lines.append(f"Total portfolio profit/loss: EUR {int(total):,}.")
    return "\n".join(lines)


@app.post("/ask")
def ask(body: schemas.ChatIn, db: Session = Depends(get_db)) -> dict:
    """Answer a question with the portfolio as context.

    If project_id is a program (has children), its children are the context.
    Otherwise we use the project's own siblings/parent so the LLM still has context.
    """
    if body.project_id is None:
        raise HTTPException(400, "project_id is required for a context answer")
    parent = _get_project(db, body.project_id)
    children = list(
        db.scalars(select(Project).where(Project.parent_id == parent.id)).all()
    )
    if not children and parent.parent_id is not None:
        # Use the parent's portfolio as context for a leaf node.
        grandparent = db.get(Project, parent.parent_id)
        siblings = list(
            db.scalars(select(Project).where(Project.parent_id == parent.parent_id)).all()
        )
        context = _portfolio_context(grandparent, siblings)
    else:
        context = _portfolio_context(parent, children)

    # Unified navigator turn: apply any parameter change AND answer concretely.
    current = {f: getattr(parent, f) for f in EDITABLE_FIELDS}
    result = llm.converse(body.message, current, context)
    reply = (result.get("reply") or "").strip()
    updates = result.get("updates") or {}

    applied = {}
    for field in EDITABLE_FIELDS:
        if field in updates and updates[field] is not None:
            setattr(parent, field, updates[field])
            applied[field] = updates[field]
    if applied:
        parent.audit_entries.append(
            AuditLog(
                actor="navigator",
                action="edited-from-chat",
                detail=", ".join(f"{k}={v}" for k, v in applied.items())[:480],
            )
        )

    # The bot message records the reply plus a confirmation of what changed.
    bot_text = reply
    if applied:
        change = ", ".join(f"{k} to {v}" for k, v in applied.items())
        bot_text = (reply + "\n\n" if reply else "") + f"Updated {change}."

    db.add(ChatMessage(project_id=parent.id, role="user", text=body.message))
    db.add(ChatMessage(project_id=parent.id, role="bot", text=bot_text or "(no change)"))
    db.commit()
    if applied:
        store.export_json(db)

    return {
        "answer": bot_text,
        "applied_fields": applied,
        "status": status_engine.evaluate(parent),
        "mock_mode": config.LLM_MOCK,
    }

    return {"answer": answer, "drift": drift, "mock_mode": config.LLM_MOCK}


@app.get("/projects/{project_id}/chat")
def get_chat(project_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """The saved 'Ask about this portfolio' history for a project, oldest first."""
    _get_project(db, project_id)
    msgs = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.id)
    ).all()
    return [{"id": m.id, "role": m.role, "text": m.text,
             "timestamp": m.timestamp.isoformat()} for m in msgs]


@app.delete("/projects/{project_id}/chat")
def clear_chat(project_id: int, db: Session = Depends(get_db)) -> dict:
    """Clear the saved chat history for a project."""
    _get_project(db, project_id)
    for m in db.scalars(
        select(ChatMessage).where(ChatMessage.project_id == project_id)
    ).all():
        db.delete(m)
    db.commit()
    return {"ok": True}


# --- add-node workflow: analyze a concern, then create a neutral node ----------

@app.post("/analyze")
def analyze(body: schemas.AnalyzeIn) -> dict:
    """Intake a new project. Safety and slot-filling are handled in the LLM prompt.

    The prompt defines the assistant's role, treats user input as data (not
    instructions), politely refuses bad intent, and keeps asking for the hard
    requirements (name, goal, budget, time) until it has them, then returns a
    verdict. See llm.analyze_idea.
    """
    if not (body.idea or "").strip():
        return {
            "status": "needs_input",
            "collected": {"name": None, "goal": None, "budget_eur": None, "time_weeks": None},
            "missing": list(llm.REQUIRED_FIELDS),
            "question": "Describe the project you want to add.",
            "mock_mode": config.LLM_MOCK,
        }
    result = llm.analyze_idea(body.idea, body.history)
    result["mock_mode"] = config.LLM_MOCK
    return result


@app.post("/projects/add-node", response_model=schemas.ProjectOut, status_code=201)
def add_node(body: schemas.AddNodeIn, db: Session = Depends(get_db)) -> Project:
    """Create a new project node under a parent. No forecast yet, so it is grey."""
    parent = _get_project(db, body.parent_id)
    p = Project(
        name=body.name,
        description=body.description,
        owner="",
        status="Active",
        parent_id=parent.id,
        uncertainty_type=body.uncertainty_type,
        money_committed=body.money_committed,
        money_spent=0.0,
        reputation_tier=body.reputation_tier,
        relationships_tier=body.relationships_tier,
        reversibility_tier=body.reversibility_tier,
        pnl_eur=None,  # grey / neutral: no profit forecast yet
    )
    db.add(p)
    db.flush()
    p.audit_entries.append(
        AuditLog(actor="user", action="added-node", detail=f"{p.name} (no forecast yet)")
    )
    db.commit()
    store.export_json(db)
    return p


# --- re-commitment decision (no silent continuation) --------------------------

@app.post("/projects/{project_id}/decision")
def log_decision(
    project_id: int, body: schemas.DecisionIn, db: Session = Depends(get_db)
) -> dict:
    p = _get_project(db, project_id)
    decision = body.decision.strip().lower()
    if decision not in ("continue", "stop"):
        raise HTTPException(400, "decision must be 'continue' or 'stop'")
    p.last_decision_at = datetime.now(timezone.utc)
    if decision == "stop":
        p.status = "Stopped"
    p.audit_entries.append(
        AuditLog(
            actor=body.actor,
            action=f"decision:{decision}",
            detail=body.note or f"Explicit {decision} decision logged.",
        )
    )
    db.commit()
    store.export_json(db)
    return {"ok": True, "status": status_engine.evaluate(p)}


# --- audit log -----------------------------------------------------------------

@app.get("/projects/{project_id}/audit", response_model=list[schemas.AuditOut])
def get_audit(project_id: int, db: Session = Depends(get_db)):
    p = _get_project(db, project_id)
    return p.audit_entries


# --- comparison across experiments --------------------------------------------

@app.get("/compare")
def compare(ids: str, db: Session = Depends(get_db)) -> dict:
    """
    Compare experiments side by side across the 5 loss dimensions.
    Supports human judgment; deliberately does NOT rank or pick a winner.
    Usage: /compare?ids=1,3,5
    """
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(400, "ids must be comma-separated integers, e.g. ids=1,3")
    items = []
    for pid in id_list:
        p = _get_project(db, pid)
        st = status_engine.evaluate(p)
        items.append(
            {
                "id": p.id,
                "name": p.name,
                "overall_tier": st["overall_tier"],
                "dimensions": st["dimensions"],
                "recommit_required": st["recommit_required"],
            }
        )
    return {
        "items": items,
        "note": "Comparison supports judgment. The tool does not rank or decide.",
    }


# --- scenarios (scripted walkthrough) -----------------------------------------

@app.get("/scenarios")
def list_scenarios() -> dict:
    return {
        key: {"title": s["title"], "steps": len(s["steps"]), "project_name": s["project_name"]}
        for key, s in seed.SCENARIOS.items()
    }


@app.get("/scenarios/{key}")
def get_scenario(key: str, db: Session = Depends(get_db)) -> dict:
    scenario = seed.SCENARIOS.get(key)
    if not scenario:
        raise HTTPException(404, "Unknown scenario")
    # attach the live project id so the frontend can deep-link to it
    proj = db.scalar(select(Project).where(Project.name == scenario["project_name"]))
    return {
        "key": key,
        "title": scenario["title"],
        "project_id": proj.id if proj else None,
        "steps": scenario["steps"],
    }


# --- "would it have changed the outcome?" (challenge acceptance test) ----------

@app.get("/cases/{key}/outcome")
def case_outcome(key: str, db: Session = Depends(get_db)) -> dict:
    """The counterfactual for a case study: what the team actually did and its
    cost, versus the affordable-loss guidance the tool produces from the same
    data. The `tool` block is computed live so it is real, not hard-coded."""
    meta = seed.CASE_OUTCOMES.get(key)
    if not meta:
        raise HTTPException(404, "Unknown case")
    proj = db.scalar(select(Project).where(Project.name == meta["project_name"]))
    if not proj:
        raise HTTPException(404, "Case project not seeded")

    children = list(db.scalars(select(Project).where(Project.parent_id == proj.id)).all())
    status = status_engine.evaluate(proj)

    tool: dict = {
        "recommended_action": status["recommended_action"],
        "overall_tier": status["overall_tier"],
    }

    if key == "kodak":
        tool["verdict"] = status_engine.single_verdict(proj, status)
        tool["next_step"] = (
            f"Talk to {proj.contact_person}. Ask: {proj.contact_question} "
            f"Keep going if {proj.signal_keep}"
        )
        facts = (
            f"Project: {proj.name}. Money we can absorb: EUR {int(proj.money_committed):,}. "
            f"Money already spent: EUR {int(proj.money_spent):,}. "
            f"Time boundary: {proj.time_committed_weeks:g} weeks. "
            f"Overall risk: {status['overall_tier']}. "
            f"Re-commitment required: {status['recommit_required']}. "
            f"Smallest test: {proj.smallest_test}"
        )
        tool["reframe"] = llm.reframe_case(meta["wrong_question"], facts)

    elif key == "google":
        verdict, roll = status_engine.portfolio_verdict(proj, children)
        tool["verdict"] = verdict
        tool["boundary_breached"] = roll["boundary_breached"]
        tool["portfolio_flags"] = roll["portfolio_flags"]
        facts = (
            f"Program: {proj.name}. {len(children)} sub-projects. "
            f"Sub-project money committed totals EUR {int(roll['totals']['money_committed']):,} "
            f"against a program boundary of EUR {int(roll['program_boundary']['money_committed']):,}. "
            f"Boundary breached: {roll['boundary_breached']}."
        )
        tool["reframe"] = llm.reframe_case(meta["wrong_question"], facts)

    elif key == "sony":
        verdict, views = status_engine.stakeholder_verdict(proj.stakeholders)
        tool["verdict"] = verdict
        tool["stakeholder_views"] = views
        facts = (
            f"Project: {proj.name}. Stakeholders and their overall affordable-loss tier: "
            + "; ".join(f"{v['name']} ({v['role']}) = {v['overall_tier']}, "
                        f"money exposure {v['money_tier']}" for v in views)
        )
        tool["reframe"] = llm.reframe_case(meta["wrong_question"], facts)

    return {
        "key": key,
        "project_id": proj.id,
        "historical": {
            "wrong_question": meta["wrong_question"],
            "actual_decision": meta["actual_decision"],
            "cost": meta["cost"],
        },
        "tool": tool,
        "averted": meta["averted"],
        "mock_mode": config.LLM_MOCK,
    }
