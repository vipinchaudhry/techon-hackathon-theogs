"""
Seed the three demo case studies: Kodak, Google, Sony.

Run automatically on startup if the DB is empty, or force a reset via the
POST /reset endpoint. Numbers are illustrative but chosen to make each case's
teaching point fire in the status engine.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditLog, Project, Stakeholder


def _audit(project: Project, action: str, detail: str, actor: str = "system", days_ago: int = 0):
    project.audit_entries.append(
        AuditLog(
            actor=actor,
            action=action,
            detail=detail,
            timestamp=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
    )


def seed_kodak(db: Session) -> Project:
    """Kodak: a single decision. Reframe ROI into Affordable Loss and produce a
    concrete first step. No sub-projects, this is the one bet to focus on."""
    k = Project(
        name="Kodak — Filmless (Digital) Camera",
        description=(
            "Steven Sasson's prototype digital camera. Executives keep asking what the "
            "expected return is and how much revenue a filmless camera would bring, "
            "which makes it look like a way to destroy the film business."
        ),
        owner="Steven Sasson",
        status="Active",
        uncertainty_type="Market",
        money_committed=50_000,
        money_spent=5_000,
        time_committed_weeks=12,
        time_spent_weeks=2,
        reputation_tier="Medium",
        relationships_tier="Low",
        reversibility_tier="Low",
        hypothesis="A small group of photographers would value instant, filmless images enough to pay.",
        smallest_test="Show the prototype to 5 pro photographers and 2 retail buyers.",
        contact_person="A pro wedding photographer and one camera-store buyer",
        contact_question="If this were filmless, what would make it useful enough to switch?",
        signal_keep="At least 3 of 7 ask to try it on a real job.",
        signal_stop="All 7 say film quality is non-negotiable for years.",
        reevaluation_date=date.today() + timedelta(days=21),
    )
    _audit(k, "created", "Seeded Kodak digital camera case.", days_ago=3)
    db.add(k)
    return k


def seed_google(db: Session) -> Project:
    """Portfolio rollup: a program whose loss boundary erodes across many sub-projects."""
    program = Project(
        name="Google — 20% Time Program",
        description=(
            "Engineers spend ~one day a week on self-chosen projects. No single project "
            "looks dangerous, but we need to watch the health of the program as a whole."
        ),
        owner="Eng Leadership",
        status="Active",
        uncertainty_type="Resource",
        # PROGRAM boundary: what the org can absorb across the whole program.
        money_committed=2_000_000,
        money_spent=0,
        time_committed_weeks=2_000,  # total engineer-weeks the program can absorb
        time_spent_weeks=0,
        reputation_tier="Low",
        relationships_tier="Low",
        reversibility_tier="Low",
        hypothesis="Bottom-up exploration produces breakout products faster than central planning.",
        smallest_test="Track each 20% project's loss profile and roll it up monthly.",
        contact_person="Eng managers running 20% projects",
        contact_question="Is your 20% project still getting real time, or is it 120% time now?",
        signal_keep="Program-level commitments stay within the affordable boundary.",
        signal_stop="Sub-project commitments quietly exceed the program boundary.",
        reevaluation_date=date.today() + timedelta(days=30),
    )
    db.add(program)
    db.flush()  # get program.id

    # A spread of sub-projects. Together they OVER-COMMIT the program boundary,
    # even though each one alone looks fine. Green = in profit, red = in loss.
    # (name, pnl_eur, money_committed, money_spent, weeks_committed, weeks_spent, reputation)
    subs = [
        ("Gmail", 900_000, 400_000, 380_000, 400, 360, "Medium"),
        ("AdSense", 1_200_000, 500_000, 450_000, 350, 330, "High"),
        ("Google News", 120_000, 250_000, 240_000, 300, 290, "Low"),
        ("Google Talk", -80_000, 200_000, 180_000, 250, 240, "Low"),
        ("Google Sky", -60_000, 150_000, 120_000, 200, 180, "Low"),
        ("Google Transit", 40_000, 220_000, 200_000, 260, 250, "Low"),
        ("Misc 20% (long tail)", -210_000, 600_000, 520_000, 700, 650, "Medium"),
    ]
    for name, pnl, mc, ms, tc, ts, rep in subs:
        losing = pnl < 0
        child = Project(
            name=name,
            description=(
                f"A 20%-time project. Currently {'losing' if losing else 'making'} "
                f"money (EUR {pnl:,})."
            ),
            owner="Various engineers",
            status="Active",
            parent_id=program.id,
            uncertainty_type="Market",
            money_committed=mc,
            money_spent=ms,
            time_committed_weeks=tc,
            time_spent_weeks=ts,
            reputation_tier=rep,
            relationships_tier="Low",
            reversibility_tier="Low",
            pnl_eur=pnl,
            reevaluation_date=date.today() + timedelta(days=14),
        )
        db.add(child)

    _audit(program, "created", "Seeded Google 20% program with 7 sub-projects.", days_ago=5)
    return program


def seed_sony(db: Session) -> Project:
    """Multi-stakeholder: same project, very different loss profiles per person."""
    s = Project(
        name="Sony — PlayStation (Kutaragi's side project)",
        description=(
            "A junior engineer's unauthorized console project. The team and the "
            "executive sponsor have completely different stakes in whether it continues."
        ),
        owner="Ken Kutaragi",
        status="Active",
        uncertainty_type="Stakeholder",
        money_committed=300_000,
        money_spent=120_000,
        time_committed_weeks=80,
        time_spent_weeks=30,
        reputation_tier="High",
        relationships_tier="High",
        reversibility_tier="Medium",
        hypothesis="Sony can build a standalone console that beats existing game hardware.",
        smallest_test="Build one working standalone prototype and demo it internally.",
        contact_person="Norio Ohga (president / sponsor)",
        contact_question="Will you protect this project's affordable-loss boundary against the board?",
        signal_keep="Sponsor commits to shield the team after the Nintendo/Philips snub.",
        signal_stop="Sponsor support withdrawn; team left exposed.",
        reevaluation_date=date.today() + timedelta(days=10),
    )
    s.stakeholders = [
        Stakeholder(
            name="Ken Kutaragi",
            role="Team",
            stake_note="Bet his career and standing inside Sony. Already over-committed.",
            money_tier="Low",
            time_tier="High",
            reputation_tier="Critical",
            relationships_tier="High",
            reversibility_tier="High",
        ),
        Stakeholder(
            name="Norio Ohga",
            role="Sponsor",
            stake_note="Company-level bet. Can absorb money; risks political capital with the board.",
            money_tier="High",
            time_tier="Low",
            reputation_tier="Medium",
            relationships_tier="High",
            reversibility_tier="Medium",
        ),
        Stakeholder(
            name="Sony Board / Steering",
            role="Steering",
            stake_note="Sees a junior engineer working with a competitor; reputational downside.",
            money_tier="Medium",
            time_tier="Low",
            reputation_tier="High",
            relationships_tier="Critical",
            reversibility_tier="Low",
        ),
    ]
    _audit(s, "created", "Seeded Sony case with 3 stakeholders.", days_ago=2)
    db.add(s)
    return s


def seed_all(db: Session, force: bool = False) -> None:
    existing = db.scalar(select(Project).limit(1))
    if existing and not force:
        return
    if force:
        # wipe everything
        for p in db.scalars(select(Project)).all():
            db.delete(p)
        db.flush()
    seed_kodak(db)
    seed_google(db)
    seed_sony(db)
    db.commit()


# --- scripted demo walkthroughs (challenge: scripted walkthrough) -------------
# Each step has narration + a hint of what to look at on screen. The frontend
# steps through these for the pitch. They reference seeded projects by name.

SCENARIOS = {
    "kodak": {
        "title": "Kodak: Reframe the room",
        "project_name": "Kodak — Filmless (Digital) Camera",
        "steps": [
            {"title": "The wrong question",
             "narration": "Executives ask: what is the expected return on a filmless camera? Against that question it looks like a way to destroy the film business. So they bury it."},
            {"title": "The Navigator reframes",
             "narration": "The tool replaces the ROI question with: what is the smallest amount we could put on the table to find out if digital is real, while staying genuinely fine if it fails?"},
            {"title": "What is at stake",
             "narration": "Money: 50k we can absorb. Time: 12 weeks. Reputation: Medium. Nothing here threatens the film business. The bet-the-company framing was an illusion."},
            {"title": "A concrete next step",
             "narration": "Not 'run an experiment.' Instead: show the prototype to 5 pro photographers and 2 retail buyers this month, and ask one specific question. Keep going if 3 of 7 want to try it on a real job."},
            {"title": "Would it have changed 1976?",
             "narration": "Yes. The decision stops being 'launch vs protect film' and becomes 'spend 50k to learn.' That is a decision executives can say yes to."},
        ],
    },
    "google": {
        "title": "Google (2008): Watch the program bleed out",
        "project_name": "Google — 20% Time Program",
        "steps": [
            {"title": "Every project looks fine",
             "narration": "Open any single 20% project. Its loss profile is healthy. This is why nobody panicked — and why the program died silently."},
            {"title": "Roll it up",
             "narration": "The Navigator sums the sub-projects against the PROGRAM's affordable-loss boundary. Individually fine; together they have crossed the line."},
            {"title": "The portfolio flag fires",
             "narration": "Total sub-project commitments exceed the program boundary. Seven active projects, no single dangerous one — exactly the Google failure pattern."},
            {"title": "The signal a 2008 manager needed",
             "narration": "'Your 20% program has quietly crossed its affordable-loss boundary across 7 projects.' That sentence, on a screen, is what was missing."},
            {"title": "Would it have changed the outcome?",
             "narration": "A program-level boundary breach demands an explicit re-commitment — instead of a thousand small, silent decisions ending 20% time."},
        ],
    },
    "sony": {
        "title": "Sony (late 1980s): Different stakes, different screens",
        "project_name": "Sony — PlayStation (Kutaragi's side project)",
        "steps": [
            {"title": "One project, many stakes",
             "narration": "Kutaragi bet his career. Ohga is making a company-level bet. The board sees a reputational risk. Same project, three different loss profiles."},
            {"title": "Act as Kutaragi",
             "narration": "Switch to Kutaragi's view: reputation = Critical, time = High. For him this is nearly irreversible — he's already all-in."},
            {"title": "Act as Ohga",
             "narration": "Switch to Ohga's view: money = High but absorbable, reputation = Medium. He can afford the loss the team cannot. That's why the decision belongs to him."},
            {"title": "The tool refuses to collapse them",
             "narration": "No single shared number. The Navigator shows each stakeholder their own affordable loss — supporting judgment instead of averaging it away."},
            {"title": "Would it have changed the outcome?",
             "narration": "It makes explicit what Ohga saw intuitively: the sponsor's affordable loss, not the team's, is the one that should drive 'continue.'"},
        ],
    },
}
