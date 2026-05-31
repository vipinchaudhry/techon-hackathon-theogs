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
    """Kodak as a project portfolio: one program with 10 project nodes.

    Each node carries a profit/loss number. Green = in profit, red = in loss.
    This is the manager view: see the whole portfolio at a glance as a graph.
    """
    program = Project(
        name="Kodak Portfolio",
        description=(
            "Kodak's bets across film and digital. Each node is a project. Green nodes "
            "make money, red nodes lose it. The question is which bets we can afford."
        ),
        owner="Kodak Leadership",
        status="Active",
        uncertainty_type="Market",
        money_committed=3_000_000,
        money_spent=0,
        time_committed_weeks=1_200,
        time_spent_weeks=0,
        reputation_tier="Medium",
        relationships_tier="Low",
        reversibility_tier="Low",
        hypothesis="A balanced portfolio funds digital exploration from film profits.",
        smallest_test="Track each project's profit/loss and affordable loss monthly.",
        contact_person="Each project owner",
        contact_question="Is this project still within what we can afford to lose?",
        signal_keep="Film profits cover the digital bets we choose to keep.",
        signal_stop="Loss-making bets exceed what the portfolio can absorb.",
        reevaluation_date=date.today() + timedelta(days=21),
    )
    db.add(program)
    db.flush()

    # (name, pnl_eur, money_committed, money_spent, weeks_committed, weeks_spent,
    #  reputation, uncertainty, status)
    nodes = [
        ("Color Film (consumer)", 1_400_000, 200_000, 180_000, 60, 58, "Low", "Market", "Active"),
        ("Film Processing Labs", 820_000, 150_000, 140_000, 80, 78, "Low", "Resource", "Active"),
        ("Photo Paper", 360_000, 90_000, 85_000, 50, 48, "Low", "Market", "Active"),
        ("Single-Use Cameras", 240_000, 70_000, 60_000, 40, 35, "Low", "Market", "Active"),
        ("Digital Camera (Sasson)", -180_000, 50_000, 48_000, 12, 11, "Medium", "Market", "Active"),
        ("DSLR Prototype", -260_000, 120_000, 118_000, 90, 88, "High", "Technology", "Active"),
        ("Inkjet Printers", -140_000, 110_000, 90_000, 60, 40, "Medium", "Technology", "Active"),
        ("Online Photo Sharing", -90_000, 80_000, 60_000, 30, 22, "Medium", "Market", "Active"),
        ("Kiosk Printing", 60_000, 40_000, 30_000, 25, 20, "Low", "Resource", "Active"),
        ("Chemicals Division", 510_000, 130_000, 120_000, 70, 68, "Low", "Resource", "Active"),
    ]
    for (name, pnl, mc, ms, tc, ts, rep, unc, st) in nodes:
        losing = pnl < 0
        child = Project(
            name=name,
            description=(
                f"{name}: currently {'losing' if losing else 'making'} money "
                f"(EUR {pnl:,}). Part of the Kodak portfolio."
            ),
            owner="Project owner",
            status=st,
            parent_id=program.id,
            uncertainty_type=unc,
            money_committed=mc,
            money_spent=ms,
            time_committed_weeks=tc,
            time_spent_weeks=ts,
            reputation_tier=rep,
            relationships_tier="Low",
            reversibility_tier="Medium" if losing else "Low",
            pnl_eur=pnl,
            hypothesis=f"{name} earns its place in the portfolio.",
            smallest_test="Review this quarter's profit/loss against its affordable loss.",
            contact_person="Project owner",
            contact_question="What would tell us to double down or stop?",
            signal_keep="Profit holds or the loss stays within what we can absorb.",
            signal_stop="Loss grows past the affordable boundary.",
            reevaluation_date=date.today() + timedelta(days=14),
        )
        db.add(child)

    _audit(program, "created", "Seeded Kodak portfolio with 10 project nodes.", days_ago=3)
    return program


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
    # even though each one alone looks fine — the silent-erosion signal.
    subs = [
        ("Gmail", 400_000, 380_000, 400, 360, "Medium"),
        ("Google News", 250_000, 240_000, 300, 290, "Low"),
        ("AdSense", 500_000, 450_000, 350, 330, "High"),
        ("Google Talk", 200_000, 180_000, 250, 240, "Low"),
        ("Google Sky", 150_000, 120_000, 200, 180, "Low"),
        ("Google Transit", 220_000, 200_000, 260, 250, "Low"),
        ("Misc 20% (long tail)", 600_000, 520_000, 700, 650, "Medium"),
    ]
    for name, mc, ms, tc, ts, rep in subs:
        child = Project(
            name=f"20% — {name}",
            description=f"A 20%-time project: {name}.",
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
        "title": "Kodak: The portfolio view",
        "project_name": "Kodak Portfolio",
        "steps": [
            {"title": "Ten bets, one map",
             "narration": "Kodak ran many projects at once. Here they are as nodes. Green nodes make money, red nodes lose it. You see the whole portfolio in one glance."},
            {"title": "Film pays, digital costs",
             "narration": "The big green nodes are film. The red nodes are the digital bets: the Sasson camera, the DSLR, inkjet. They lose money now, but they are the future."},
            {"title": "The wrong question",
             "narration": "Executives ask 'what is the ROI on the red nodes?' and want to cut them. But ROI is unknowable here. The real question is what we can afford to lose."},
            {"title": "Affordable, not killable",
             "narration": "Film profits easily cover the digital losses. Kept small, these red bets are affordable. Cutting them is what eventually sank the company."},
            {"title": "What changes",
             "narration": "The portfolio view turns 'kill the money-losers' into 'fund the future from the present.' That is the decision Kodak missed."},
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
