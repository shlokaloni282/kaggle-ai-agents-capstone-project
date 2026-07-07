import re

# Word/phrase-boundary regex patterns instead of plain substring checks,
# so we don't false-positive on partial word matches and so multi-word
# phrases still match regardless of exact spacing/punctuation.
_RISK_PATTERNS = [
    r"\bsuicid\w*\b",
    r"\bkill(ing)?\s+myself\b",
    r"\bhurt(ing)?\s+myself\b",
    r"\bend\s+(it\s+all|my\s+life)\b",
    r"\bself[\s-]?harm\w*\b",
    r"\bwant(ed)?\s+to\s+die\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bcan'?t\s+go\s+on\b",
]

_RISK_RE = re.compile("|".join(_RISK_PATTERNS), re.IGNORECASE)


def safety_check(message: str) -> bool:
    """Deterministic keyword/pattern check for crisis language.

    Runs BEFORE the LLM pipeline so it can't be talked out of firing,
    doesn't depend on the model noticing anything, and costs no API call.
    """
    return bool(_RISK_RE.search(message or ""))


def safety_response() -> str:
    return """
I'm really glad you shared this with me.

I'm not a replacement for professional support, but you deserve help and
support right now.

If you feel unsafe or are in immediate danger:
India Emergency: 112

You can also reach out to a mental health helpline or a trusted person
near you. I'm here to keep talking whenever you're ready.
"""