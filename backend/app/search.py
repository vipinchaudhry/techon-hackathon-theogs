"""
Optional web search for the advice sessions.

If a Tavily API key is present (TAVILY_API_KEY env var, or a tvly- token in
api.md), the Navigator can pull a few fresh web snippets to ground its advice.
Without a key, available() is False and the caller simply reasons from the
portfolio. This keeps the app fully functional offline and adds search only when
configured.
"""

import httpx

from . import config


def available() -> bool:
    return bool(config.TAVILY_API_KEY)


def search(query: str, max_results: int = 4) -> str:
    """Return a short text block of web findings for `query`, or "" if search is
    unavailable or fails. Never raises."""
    if not available():
        return ""
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": config.TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return ""

    lines = []
    if data.get("answer"):
        lines.append("Summary: " + data["answer"])
    for r in data.get("results", [])[:max_results]:
        title = r.get("title", "")
        content = (r.get("content", "") or "")[:300]
        lines.append(f"- {title}: {content}")
    return "\n".join(lines)
