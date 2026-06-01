"""
Central configuration. Everything tunable lives here so there is one place to look.

Reads, in order of priority:
  1. real environment variables
  2. a local .env file (optional)
  3. the OpenRouter key from ../api.md (the file the team drops the key into)

If no key is found anywhere, the app runs in MOCK mode: no network calls, no cost.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> backend/app -> backend -> techon
TECHON_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

# Load a .env file from the backend folder if present (optional).
load_dotenv(BACKEND_DIR / ".env")


def _read_token_from_api_md(prefix: str) -> str | None:
    """Grab a token with a given prefix (e.g. 'xoxb-', 'xapp-') from api.md.

    Accepts labeled lines (SLACK_BOT_TOKEN=xoxb-...) or the bare token.
    """
    api_md = TECHON_DIR / "api.md"
    if not api_md.exists():
        return None
    text = api_md.read_text(encoding="utf-8")
    match = re.search(re.escape(prefix) + r"[A-Za-z0-9\-]+", text)
    return match.group(0) if match else None


def _read_key_from_api_md() -> str | None:
    """
    The team agreed to put the OpenRouter key in techon/api.md.

    We are deliberately forgiving about the format so there are no hiccups. Any of
    these (and most variants) work, with or without a label, fences, or bullets:

        sk-or-v1-xxxxxxxx
        OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
        OpenRouter API: sk-or-v1-xxxxxxxx
        - key: sk-or-v1-xxxxxxxx

    The strategy: ignore any label entirely and just grab the first token that
    looks like a key (starts with "sk-or" or "sk-") anywhere in the file.
    """
    api_md = TECHON_DIR / "api.md"
    if not api_md.exists():
        return None
    text = api_md.read_text(encoding="utf-8")
    # Find a key-shaped token regardless of what label precedes it.
    match = re.search(r"sk-or[\w\-]+|sk-[\w\-]{16,}", text)
    if match:
        return match.group(0)
    return None


# --- LLM / OpenRouter settings -------------------------------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or _read_key_from_api_md()

OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)

# One config var for the model. During testing we use the cheapest option.
# Override by setting LLM_MODEL in the environment or backend/.env.
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-lite-001")

# A smarter model for the advice sessions (consult/follow-up), where quality
# matters most. Falls back to LLM_MODEL if not set.
LLM_SMART_MODEL = os.getenv("LLM_SMART_MODEL", "openai/gpt-4o-mini")

# Optional web search. If a Tavily key is present (env or api.md), the advice
# sessions can search the internet; otherwise they reason from the portfolio.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") or _read_token_from_api_md("tvly-")

# Force mock mode (no network, no spend) even if a key exists: set LLM_MOCK=1.
# If there is no key at all, we are always in mock mode.
LLM_MOCK = os.getenv("LLM_MOCK") == "1" or OPENROUTER_API_KEY is None

# Soft guardrail for the $20 testing budget. We do not bill you; this is just a
# visible counter the app refuses to cross so a runaway loop can't drain credit.
LLM_TEST_BUDGET_USD = float(os.getenv("LLM_TEST_BUDGET_USD", "20"))


# --- Slack -------------------------------------------------------------------
# Bot token (xoxb-) and app-level token (xapp-, for Socket Mode). Put them in
# techon/api.md or as env vars. No public URL needed with Socket Mode.
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN") or _read_token_from_api_md("xoxb-")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN") or _read_token_from_api_md("xapp-")


# --- Database ------------------------------------------------------------------

# Defaults to a local SQLite file so the app runs with ZERO setup.
# To use Postgres instead, set:
#   DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/navigator
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'navigator.db').as_posix()}"
)


def status_summary() -> dict:
    """Small dict the frontend can show so the team always knows the mode."""
    return {
        "llm_mock": LLM_MOCK,
        "llm_model": None if LLM_MOCK else LLM_MODEL,
        "key_loaded": OPENROUTER_API_KEY is not None,
        "database": "sqlite" if DATABASE_URL.startswith("sqlite") else "postgres",
        "test_budget_usd": LLM_TEST_BUDGET_USD,
    }
