"""
Long-term memory layer.

WHY: InMemorySessionService is wiped the moment the script exits -- it
cannot be what the pitch means by "mood history across sessions." This is
a small JSON-file store, one file per user, that survives restarts. Good
enough for a free capstone submission; swap for Firestore/SQLite if this
ever runs as a real deployed service.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _path(user_id: str) -> Path:
    safe = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")) or "default_user"
    return DATA_DIR / f"{safe}_history.json"


def add_entry(user_id: str, entry: dict) -> None:
    """Append one day's check-in data to the user's persistent history."""
    p = _path(user_id)
    history = json.loads(p.read_text()) if p.exists() else []
    entry = dict(entry)
    entry["timestamp"] = datetime.utcnow().isoformat()
    history.append(entry)
    p.write_text(json.dumps(history, indent=2))


def get_recent_history(user_id: str, days: int = 14) -> list:
    """Return check-in entries from the last `days` days, oldest first."""
    p = _path(user_id)
    if not p.exists():
        return []
    history = json.loads(p.read_text())
    cutoff = datetime.utcnow() - timedelta(days=days)
    return [e for e in history if datetime.fromisoformat(e["timestamp"]) >= cutoff]


def get_recent_history_summary(user_id: str, days: int = 14) -> str:
    """Human-readable summary for injecting into an LLM prompt via state."""
    history = get_recent_history(user_id, days)
    if not history:
        return "No prior check-ins on record yet -- this is the first one."
    lines = [
        f"- {e['timestamp'][:10]}: mood={e.get('mood')}, stress={e.get('stress')}, "
        f"sleep={e.get('sleep_quality')}, energy={e.get('energy_level')}"
        for e in history
    ]
    return f"Last {len(history)} check-in(s):\n" + "\n".join(lines)