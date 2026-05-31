"""
Slack transport for the Navigator guardrail. Socket Mode = no public URL needed.

Run from backend/:  .venv/bin/python -m app.slackbot

Commands (in any channel the bot is in, or its DM):
  /navigator new        -> start the demo project (AI Support Pilot) in this channel
  /navigator simulate   -> advance the demo clock; the bot escalates if ignored
  /navigator status     -> show the current affordable-loss profile
  /navigator reset      -> clear the project in this channel

  @Navigator <message>  -> adjust a parameter or ask (e.g. "budget dropped 5k")
  keep / stop / resume  -> log an explicit decision (resets / unfreezes)

All the real logic lives in guardian.py and llm.py; this file is just wiring.
"""

import sys

from sqlalchemy import select

from . import config, guardian, llm
from .db import Base, SessionLocal, engine
from .models import Project, ChatMessage

try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:  # pragma: no cover
    print("slack_bolt not installed. Run: .venv/bin/pip install slack_bolt")
    sys.exit(1)


def _project_for_channel(db, channel: str) -> Project | None:
    return db.scalar(select(Project).where(Project.slack_channel == channel))


def _seed_demo(db, channel: str) -> Project:
    """Create the canned AI Support Pilot demo project bound to this channel."""
    existing = _project_for_channel(db, channel)
    if existing:
        db.delete(existing)
        db.commit()
    p = Project(
        name="AI Support Pilot",
        description="An internal pilot: AI drafts customer support replies.",
        owner="",
        sponsor="the COO",
        status="Active",
        uncertainty_type="Market",
        slack_channel=channel,
        money_committed=15000, money_spent=2000,
        time_committed_weeks=8, time_spent_weeks=1,
        reputation_tier="Medium",
        hypothesis="Support agents will reuse an AI drafter if it saves real time.",
        smallest_test="3 agents use it on 20 real tickets this week.",
        contact_person="3 support agents",
        contact_question="would you want to keep using this?",
        signal_keep="agents reuse it without being asked",
        signal_stop="it creates more cleanup than it saves",
    )
    db.add(p)
    db.commit()
    return p


def build_app() -> "App":
    Base.metadata.create_all(bind=engine)
    app = App(token=config.SLACK_BOT_TOKEN)

    # ---- slash command ----
    @app.command("/navigator")
    def handle_cmd(ack, command, say):
        ack()
        text = (command.get("text") or "").strip().lower()
        channel = command["channel_id"]
        db = SessionLocal()
        try:
            if text.startswith("new"):
                p = _seed_demo(db, channel)
                say(
                    "I will not ask what this will *earn* — that is a guess. I track "
                    "what you can *afford to lose*.\n\n" + guardian.profile_text(p)
                )
                say("✅ *Next step:* " + guardian.next_step_text(p))
                say(
                    "I am watching this now. Tell me when things change "
                    "(e.g. _budget dropped by 5k_), or type `/navigator simulate` "
                    "to fast-forward time."
                )
            elif text.startswith("sim"):
                p = _project_for_channel(db, channel)
                if not p:
                    say("No project here yet. Start one with `/navigator new`.")
                    return
                guardian.advance_time(db, p, weeks=2)
                pct = int(100 * guardian.consumed_ratio(p))
                res = guardian.check(db, p)
                if res["posted"]:
                    say(res["message"])
                else:
                    say(f"_Two weeks pass… {p.name} is at {pct}% of its affordable loss. "
                        f"All quiet._")
            elif text.startswith("status"):
                p = _project_for_channel(db, channel)
                say(guardian.profile_text(p) if p else "No project here. `/navigator new`.")
            elif text.startswith("reset"):
                p = _project_for_channel(db, channel)
                if p:
                    db.delete(p)
                    db.commit()
                say("Cleared. Start again with `/navigator new`.")
            else:
                say("Try `/navigator new`, `/navigator simulate`, `/navigator status`, "
                    "or `/navigator reset`.")
        finally:
            db.close()

    # ---- plain messages + mentions ----
    def _handle_text(channel: str, raw: str, say):
        msg = (raw or "").strip()
        low = msg.lower()
        db = SessionLocal()
        try:
            p = _project_for_channel(db, channel)
            if not p:
                say("No project here yet. Start one with `/navigator new`.")
                return

            # explicit decisions
            first = low.split()[0] if low.split() else ""
            if first in ("keep", "continue", "stop", "resume"):
                say(guardian.log_decision(db, p, first, actor="team", note=msg))
                return

            # otherwise: adjust a parameter or answer a question (the LLM interface)
            current = {
                "money_committed": p.money_committed, "money_spent": p.money_spent,
                "time_committed_weeks": p.time_committed_weeks,
                "time_spent_weeks": p.time_spent_weeks,
                "reputation_tier": p.reputation_tier,
                "relationships_tier": p.relationships_tier,
                "reversibility_tier": p.reversibility_tier,
            }
            context = guardian.profile_text(p)
            result = llm.converse(msg, current, context)
            applied = {}
            for f, v in (result.get("updates") or {}).items():
                if hasattr(p, f) and v is not None:
                    setattr(p, f, v)
                    applied[f] = v
            db.add(ChatMessage(project_id=p.id, role="user", text=msg))
            reply = (result.get("reply") or "").strip()
            if applied:
                reply = (reply + "\n\n" if reply else "") + "Updated " + ", ".join(
                    f"{k} to {v}" for k, v in applied.items()) + "."
            db.add(ChatMessage(project_id=p.id, role="bot", text=reply or "(noted)"))
            db.commit()
            say(reply or "Noted.")

            # after an edit, the boundary may now be crossed -> escalate immediately
            res = guardian.check(db, p)
            if res["posted"]:
                say(res["message"])
        finally:
            db.close()

    @app.event("app_mention")
    def on_mention(event, say):
        # strip the leading "<@BOTID>"
        text = event.get("text", "")
        if ">" in text:
            text = text.split(">", 1)[1]
        _handle_text(event["channel"], text, say)

    @app.event("message")
    def on_message(event, say):
        # only direct messages (im); ignore the bot's own + edits
        if event.get("bot_id") or event.get("subtype"):
            return
        if event.get("channel_type") == "im":
            _handle_text(event["channel"], event.get("text", ""), say)

    return app


def main():
    if not config.SLACK_BOT_TOKEN or not config.SLACK_APP_TOKEN:
        print("Missing Slack tokens. Put SLACK_BOT_TOKEN (xoxb-) and "
              "SLACK_APP_TOKEN (xapp-) in techon/api.md, then re-run.")
        sys.exit(1)
    app = build_app()
    print("Navigator guardrail is live on Slack (Socket Mode). Ctrl+C to stop.")
    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()


if __name__ == "__main__":
    main()
