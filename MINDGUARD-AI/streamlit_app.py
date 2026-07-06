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
import re
import sys
import time
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


# ── helpers ─────────────────────────────────────────────────────────────────

def _run_async(coro):
    """Run a coroutine synchronously from Streamlit's sync context.

    Creates a brand-new event loop in a worker thread each call.
    This is the safest pattern on Windows where the main thread's
    event loop policy can be awkward inside Streamlit.

    Includes a small delay before closing the loop to allow aiohttp
    (used by google.genai) to gracefully shut down its connections,
    preventing "Task was destroyed but it is pending!" warnings.
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
            time.sleep(0.1)  # let aiohttp close connections before closing loop
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
    """
    return re.sub(r"CHECKIN_COMPLETE\s*\n?\{[^}]*\}\s*", "", text).strip()


def _time_based_greeting() -> str:
    """Returns a warm greeting based on the current time of day."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Hi there, night owl"


RISK_COLOR = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}


# ── page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MindGuard AI",
    page_icon="🌿",
    layout="wide",
)


# ── calming green theme (loaded from external style.css) ────────────────────
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
    """Send one message and collect the full streamed response.

    Handles BOTH 429 (rate limit) and 503 (server overloaded) with
    exponential backoff, so a temporary Google-side issue doesn't
    interrupt the full pipeline (checkin → analysis → response → resources).
    """
    await asyncio.sleep(0.5)  # small buffer to avoid rapid-fire requests

    message = types.Content(
        role="user",
        parts=[types.Part(text=user_text)],
    )

    max_retries = 4  # bumped up from 2 — 503s can take a few tries to clear
    for attempt in range(max_retries):
        try:
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

        except ClientError as e:
            code = getattr(e, "code", None)
            is_last_attempt = attempt == max_retries - 1

            if code == 429 and not is_last_attempt:
                wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s, 16s
                st.toast(f"⏳ Rate limited — retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            if code == 503 and not is_last_attempt:
                wait_time = 4 + (attempt * 3)  # 4s, 7s, 10s, 13s
                st.toast(f"⏳ Google's servers are busy — retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            # Either a different error, or we've used up all retries
            raise

    return ""


runner, session_service = _build_runner()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_risk" not in st.session_state:
    st.session_state.last_risk = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None


# ── sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌿 MindGuard AI")
    st.caption("Your daily mental wellness companion")

    if not st.session_state.user_name:
        name_input = st.text_input("What should I call you?", placeholder="e.g. Shloka")
        if name_input:
            st.session_state.user_name = name_input.strip()
            st.rerun()

    st.divider()

    risk = st.session_state.last_risk
    if risk:
        icon = RISK_COLOR.get(risk, "⚪")
        color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(risk, "gray")
        st.markdown(f"**Today's risk level:** :{color}[{icon} {risk}]")
        st.divider()

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
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.session_state.last_risk = None
        st.rerun()


# ── main chat area ────────────────────────────────────────────────────────────

greeting = _time_based_greeting()
if st.session_state.user_name:
    header_text = f"{greeting}, {st.session_state.user_name} 🌿"
else:
    header_text = f"{greeting} 🌿"

st.header(header_text, divider="green")
st.caption("Take a breath. I'm here whenever you're ready to check in.")

for msg in st.session_state.chat_history:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["text"])

user_input = st.chat_input("How are you doing today?")

if user_input:
    st.session_state.chat_history.append({"role": "user", "text": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("MindGuard AI is thinking..."):
            try:
                session_id = _get_session_id(session_service)
                raw = _run_async(_call_agent(runner, session_id, user_input))

                visible = _strip_checkin_marker(raw)

                risk = _parse_risk(raw)
                if risk:
                    st.session_state.last_risk = risk

                st.markdown(visible)
                st.session_state.chat_history.append({"role": "ai", "text": visible})

            except ClientError as e:
                code = getattr(e, "code", None)

                if code == 429:
                    msg = (
                        "⏳ **Rate limit reached** — the free tier allows a limited number "
                        "of requests per minute. Wait **30-60 seconds**, then try your last "
                        "response again. (If this persists, you may have hit the daily free "
                        "tier limit — come back tomorrow!)"
                    )
                elif code == 503:
                    msg = (
                        "⏳ **Google's servers are experiencing high demand** right now, even "
                        "after several retries. This usually clears within a minute or two — "
                        "please wait and try again."
                    )
                else:
                    msg = f"API error: {e}"

                st.error(msg)
                st.session_state.chat_history.append({"role": "ai", "text": msg})

            except Exception as e:
                st.error(f"Something went wrong: {e}")