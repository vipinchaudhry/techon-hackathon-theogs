"""Deterministic input guardrails (run BEFORE any LLM call).

Goal: stop prompt injection, trolling, and junk from reaching the model, and
make sure we only spend tokens on genuine project input. This is the cheap first
line of defence; the LLM adds a second on-topic/safety check on top.
"""

import re

# Phrases that try to override instructions or extract the system prompt.
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|the\s+|your\s+|any\s+)?(previous|prior|above)?\s*(instructions|prompts?|rules)",
    r"disregard\s+(all\s+|the\s+|your\s+|previous\s+|above\s+)",
    r"forget\s+(everything|all|your\s+instructions|the\s+above)",
    r"you\s+are\s+now\b",
    r"pretend\s+(to\s+be|you\s+are)",
    r"\bact\s+as\s+(a|an|if)\b",
    r"system\s+prompt",
    r"developer\s+mode",
    r"\bjailbreak",
    r"reveal\s+(your|the)\s+(prompt|instructions|system)",
    r"print\s+(your|the)\s+(prompt|instructions)",
    r"repeat\s+(the|your)\s+(prompt|instructions|system)",
    r"new\s+instructions?\s*:",
    r"override\s+(your|the|all)",
    r"</?(system|assistant|user)>",  # fake role tags
    r"\bDAN\b",
]

# Obvious trolling / nonsense.
TROLL_PATTERNS = [
    r"\b(lol+|lmao|haha+|test+ing?|asdf+|qwerty|blah+|yolo)\b",
    r"\b(fuck|shit|bitch|stupid|idiot)\b",
]

_WORD_RE = re.compile(r"[a-zA-Z]{2,}")


def check(text: str) -> dict:
    """Return {ok: bool, reason: str, category: str}.

    category in: clean | empty | too_short | gibberish | injection | troll
    """
    raw = (text or "").strip()
    low = raw.lower()

    if not raw:
        return {"ok": False, "category": "empty",
                "reason": "Please type something to describe the project."}

    # injection first (most important)
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            return {"ok": False, "category": "injection",
                    "reason": "That looks like an attempt to change the assistant's "
                              "instructions. Describe a real project instead."}

    words = _WORD_RE.findall(raw)
    if len(raw) < 10 or len(words) < 3:
        return {"ok": False, "category": "too_short",
                "reason": "Too short to assess. Give a sentence or two about the "
                          "project, its budget, and how long it would run."}

    # gibberish: very low ratio of real-looking words to tokens, or one char repeated
    if re.search(r"(.)\1{6,}", low):
        return {"ok": False, "category": "gibberish",
                "reason": "That does not read as a real project. Please rephrase."}
    letters = sum(c.isalpha() for c in raw)
    if letters / max(len(raw), 1) < 0.4:
        return {"ok": False, "category": "gibberish",
                "reason": "That does not read as a real project. Please rephrase."}

    for pat in TROLL_PATTERNS:
        if re.search(pat, low):
            return {"ok": False, "category": "troll",
                    "reason": "Keep it to a genuine project description, please."}

    return {"ok": True, "category": "clean", "reason": ""}


def injection_only(text: str) -> dict:
    """Lighter check for free-text Q&A: allow short questions, still block
    injection attempts and fake role tags."""
    low = (text or "").strip().lower()
    if not low:
        return {"ok": False, "category": "empty", "reason": "Type a question."}
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            return {"ok": False, "category": "injection",
                    "reason": "That looks like an attempt to change the assistant's "
                              "instructions. Ask about the portfolio instead."}
    return {"ok": True, "category": "clean", "reason": ""}
