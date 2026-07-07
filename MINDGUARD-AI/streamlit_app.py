"""
MindGuard AI — Streamlit Chat Interface
----------------------------------------
Drop this file in the project root (same folder as main.py).
Run with:  streamlit run streamlit_app.py

Requires streamlit:  pip install streamlit
Everything else is already in your venv.

The trickiest part: Streamlit is synchronous but the ADK Runner is
async. The fix is to spin up a fresh asyncio event loop in a background
thread for every agent call — this is safe, avoids the Windows
"no event loop in main thread" crash, and means we never conflict
with Streamlit's own internal event handling.
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv

load_dotenv()

# Ensure imports resolve from the project root, same as main.py does.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.root_agent import root_agent  # noqa: E402
from memory.mood_store import get_recent_history  # noqa: E402

APP_NAME = "agents"
USER_ID = "user1"

# Where past chat transcripts are saved for the history browser.
# Pure local JSON, no API calls involved in reading/writing this.
TRANSCRIPT_PATH = ROOT / "data" / "chat_transcripts.json"


# ── helpers ─────────────────────────────────────────────────────────────────

def _run_async(coro):
    """Run a coroutine synchronously from Streamlit's sync context.

    Creates a brand-new event loop in a worker thread each call.
    This is the safest pattern on Windows where the main thread's
    event loop policy can be awkward inside Streamlit.
    """
    result = {}

    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["value"] = loop.run_until_complete(coro)
        except Exception as exc:
            result["error"] = exc
        finally:
            loop.close()

    import threading
    t = threading.Thread(target=_worker)
    t.start()
    t.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


def _parse_risk(text: str) -> str | None:
    """Extract LOW / MEDIUM / HIGH from analysis output."""
    m = re.search(r"RISK LEVEL:\s*\n?\s*(LOW|MEDIUM|HIGH)", text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _strip_checkin_marker(text: str) -> str:
    """Remove ONLY the internal CHECKIN_COMPLETE + JSON marker from the
    visible output — while keeping any text that comes after it (the
    analysis/response/resource agents' output, which is concatenated
    onto the same string by _call_agent).

    IMPORTANT: the previous version used text.split(marker)[0], which
    kept only the text BEFORE the marker and silently discarded
    everything after it -- including the wellness summary, coping
    response, and helpline resources. That's why the app appeared to
    "stop" right after check-in with no suggestions.
    """
    return re.sub(r"CHECKIN_COMPLETE\s*\n?\{[^}]*\}\s*", "", text).strip()


def _time_based_greeting() -> str:
    """
    Returns a warm greeting based on the current time of day.
    Morning: 5am-12pm | Afternoon: 12pm-5pm | Evening: 5pm-9pm | Night: 9pm-5am
    """
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Hi there, night owl"


def _save_transcript(risk: str):
    """Save the current chat_history as a browsable past conversation.

    Called once a check-in completes and produces a risk level. Pure
    local JSON read/write -- no API calls, so this works even mid
    rate-limit.
    """
    TRANSCRIPT_PATH.parent.mkdir(exist_ok=True)
    try:
        transcripts = (
            json.loads(TRANSCRIPT_PATH.read_text())
            if TRANSCRIPT_PATH.exists()
            else []
        )
    except Exception:
        transcripts = []

    transcripts.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "risk": risk,
        "messages": st.session_state.chat_history.copy(),
    })
    TRANSCRIPT_PATH.write_text(json.dumps(transcripts, indent=2))


def _load_transcripts() -> list[dict]:
    """Read all saved past conversations, most recent last."""
    if not TRANSCRIPT_PATH.exists():
        return []
    try:
        return json.loads(TRANSCRIPT_PATH.read_text())
    except Exception:
        return []


RISK_COLOR = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}


# ── page config ─────────────────────────────────────────────────────────────
# Must be the very first Streamlit command in the script

st.set_page_config(
    page_title="MindGuard AI",
    page_icon="🌿",
    layout="wide",
)


# ── calming green theme (loaded from external style.css) ────────────────────
# Keeping CSS in its own file makes both files easier to read and edit.

def _load_css(file_name: str):
    """Reads a CSS file from the project root and injects it into the page."""
    css_path = ROOT / file_name
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


_load_css("style.css")


# ── session state bootstrap ──────────────────────────────────────────────────

@st.cache_resource
def _build_runner():
    """Build Runner once per Streamlit process (cached across reruns)."""
    session_service = InMemorySessionService()
    _run_async(
        session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
        )
    )
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    return runner, session_service


def _get_session_id(session_service: InMemorySessionService) -> str:
    sessions = _run_async(
        session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    )
    return sessions.sessions[0].id


async def _call_agent(runner: Runner, session_id: str, user_text: str) -> str:
    """Send one message and collect the full streamed response."""
    message = types.Content(
        role="user",
        parts=[types.Part(text=user_text)],
    )
    full_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            part_text = event.content.parts[0].text or ""
            full_text += part_text
    return full_text


runner, session_service = _build_runner()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of {"role": "user"|"ai", "text": str}
if "last_risk" not in st.session_state:
    st.session_state.last_risk = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None


# ── sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌿 MindGuard AI")
    st.caption("Your daily mental wellness companion")

    # Ask for the user's name once, store it for the greeting
    if not st.session_state.user_name:
        name_input = st.text_input("What should I call you?", placeholder="e.g. Shloka")
        if name_input:
            st.session_state.user_name = name_input.strip()
            st.rerun()

    st.divider()

    # Risk level badge
    risk = st.session_state.last_risk
    if risk:
        icon = RISK_COLOR.get(risk, "⚪")
        color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(risk, "gray")
        st.markdown(f"**Today's risk level:** :{color}[{icon} {risk}]")
        st.divider()

    # Recent mood history
    st.subheader("📊 Mood history (last 7 days)")
    history = get_recent_history(USER_ID, days=7)
    if not history:
        st.caption("No history yet — complete your first check-in!")
    else:
        for entry in reversed(history[-7:]):
            date = entry.get("timestamp", "")[:10]
            mood = entry.get("mood", "?")
            stress = entry.get("stress", "?")
            sleep = entry.get("sleep_quality", "?")
            energy = entry.get("energy_level", "?")
            st.markdown(
                f"**{date}** — mood {mood}/10 · stress {stress}/10  \n"
                f"sleep: {sleep} · energy: {energy}"
            )

    st.divider()

    # ── Past conversations browser ──────────────────────────────────────
    # Reads saved transcripts from disk -- no API calls, works even
    # mid rate-limit. Selecting one loads it into chat_history so it
    # renders in the main chat area exactly like a live conversation.
    st.subheader("🕓 Past conversations")
    past_convos = list(reversed(_load_transcripts()))  # most recent first
    if past_convos:
        labels = [f"{c['date']} — {c['risk']}" for c in past_convos]
        choice = st.selectbox(
            "Load a past check-in",
            ["(current session)"] + labels,
            key="past_convo_select",
        )
        if choice != "(current session)":
            picked = past_convos[labels.index(choice)]
            if st.button("📂 Load this conversation"):
                st.session_state.chat_history = picked["messages"]
                st.session_state.last_risk = picked["risk"]
                st.rerun()
    else:
        st.caption("No saved conversations yet — complete a check-in to save one.")

    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.session_state.last_risk = None
        st.rerun()


# ── main chat area ────────────────────────────────────────────────────────────

# Time-based, personalized greeting header
greeting = _time_based_greeting()
if st.session_state.user_name:
    header_text = f"{greeting}, {st.session_state.user_name} 🌿"
else:
    header_text = f"{greeting} 🌿"

st.header(header_text, divider="green")
st.caption("Take a breath. I'm here whenever you're ready to check in.")

# Render history
for msg in st.session_state.chat_history:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["text"])

# Input
user_input = st.chat_input("How are you doing today?")

if user_input:
    # Show the user's message immediately
    st.session_state.chat_history.append({"role": "user", "text": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call the agent
    with st.chat_message("assistant"):
        with st.spinner("MindGuard AI is thinking..."):
            try:
                session_id = _get_session_id(session_service)
                raw = _run_async(_call_agent(runner, session_id, user_input))

                # Strip the internal CHECKIN_COMPLETE marker before displaying
                visible = _strip_checkin_marker(raw)

                # Extract risk level if present
                risk = _parse_risk(raw)
                if risk:
                    st.session_state.last_risk = risk

                st.markdown(visible)
                st.session_state.chat_history.append({"role": "ai", "text": visible})

                # Once a check-in completes and produces a risk level,
                # save this full conversation so it can be reloaded later
                # from the "Past conversations" browser in the sidebar.
                if risk:
                    _save_transcript(risk)

            except ClientError as e:
                if getattr(e, "code", None) == 429:
                    msg = (
                        "⏳ Rate limit reached — the free tier allows a handful of "
                        "requests per minute. Wait about 30–60 seconds, then send "
                        "your message again."
                    )
                    st.warning(msg)
                    st.session_state.chat_history.append({"role": "ai", "text": msg})
                else:
                    st.error(f"API error: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")