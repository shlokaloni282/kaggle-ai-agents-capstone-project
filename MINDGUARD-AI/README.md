# MindGuard AI

A multi-agent mental wellness check-in system built with Google's Agent
Development Kit (ADK) and Gemini. Runs a short daily mood check-in, analyzes
today's state alongside recent history, responds with warmth and practical
coping tools, and escalates to real support resources only when risk is
genuinely high.

**Track:** Agents for Good — Mental Health
**Course:** Kaggle 5-Day AI Agents Intensive: Vibe Coding with Google

## Problem

Most people don't have a low-friction, private way to notice a pattern in
their own wellbeing — like a week of bad sleep and rising stress — before it
escalates into something bigger. Daily mental health tracking tools that
exist tend to feel either clinical or too heavyweight for someone to keep up
with day after day.

## Solution

A conversational daily check-in (mood, stress, sleep, energy) that takes
under a minute, remembers your history across days, and responds like
someone who's actually paying attention — not a form, and not a diagnosis
engine. If things look genuinely high-risk, it also surfaces grounded
support resources instead of just more encouragement.

## Architecture

```
                          ┌───────────────────────────┐
                          │      User Input             │
                          └─────────────┬─────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │   MindGuardRootAgent         │
                          │ (custom orchestrator,        │
                          │  subclasses BaseAgent)        │
                          └─────────────┬─────────────┘
                                        │
                0. Deterministic safety_check() on every message
                   (security.py — runs BEFORE any LLM call)
                   If crisis language detected -> hard-coded
                   safety_response() with emergency numbers,
                   pipeline stops here for this turn.
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   1. checkin_agent           │
                          │   Asks mood / stress /        │
                          │   sleep quality / energy,     │
                          │   one question at a time.     │
                          │   Emits CHECKIN_COMPLETE       │
                          │   + JSON once all 4 collected.│
                          └─────────────┬─────────────┘
                                        │
                   If not complete yet -> orchestrator stops
                   and waits for the user's next answer.
                                        │
                                        ▼
                    entry saved to memory/mood_store.py (JSON,
                    persists across runs) + recent history pulled
                    into session state for trend detection
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   2. analysis_agent          │
                          │   Scores today's check-in     │
                          │   + recent history ->          │
                          │   RISK LEVEL: LOW/MEDIUM/HIGH │
                          └─────────────┬─────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │   3. response_agent           │
                          │   Warm, empathetic reflection.│
                          │   Can call wellness_tools       │
                          │   via MCP (breathing, grounding,│
                          │   journaling, affirmations...) │
                          └─────────────┬─────────────┘
                                        │
                          only if risk_level == "HIGH"
                                        ▼
                          ┌───────────────────────────┐
                          │   4. resource_agent           │
                          │   Recommends coping resources │
                          │   + professional/emergency     │
                          │   support framing for HIGH     │
                          │   risk days.                   │
                          └───────────────────────────┘
```

A rendered version of this diagram is included in the Writeup's media
gallery.

## ADK / course concepts used

| Concept                           | Where                                                                                                                 |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Multi-agent system (4 sub-agents) | `agents/`                                                                                                             |
| Custom orchestrator (`BaseAgent`) | `agents/root_agent.py` — gates the pipeline on check-in completion and branches to `resource_agent` only on HIGH risk |
| Session state                     | `ctx.session.state["mood_history"]`, passed into `analysis_agent`                                                     |
| Long-term memory across sessions  | `memory/mood_store.py` — JSON store, survives restarts (unlike `InMemorySessionService` alone)                        |
| MCP Server                        | `mcp_server/server.py` (FastMCP) exposing `wellness_tools.py` as callable tools                                       |
| Deterministic safety layer        | `security.py` — regex-based crisis detection, runs before any LLM call, cannot be prompt-talked out of firing         |
| Gemini as LLM backbone            | `gemini-2.5-flash-lite` across all four agents                                                                        |

## Why a custom orchestrator instead of `SequentialAgent`

ADK's `SequentialAgent` runs every sub-agent back-to-back on every single
call to `runner.run_async()` — with no way to say "check-in isn't finished,
stop here." Early in development this caused `analysis_agent`,
`response_agent`, and `resource_agent` to fire on incomplete check-in data,
burning API quota before the user had even answered all four questions.

`MindGuardRootAgent` (in `agents/root_agent.py`) fixes this by running
`checkin_agent` every turn, and only continuing to `analysis_agent` →
`response_agent` → conditionally `resource_agent` once `checkin_agent`
itself signals completion via a `CHECKIN_COMPLETE` marker.

It also conditionally runs `resource_agent` only when `analysis_agent`
reports `HIGH` risk — a real Google-Search-capable agent shouldn't fire on
an ordinary day.

## Safety notes

- The agent never diagnoses. Prompts across all agents explicitly instruct
  against medical/clinical language.
- `security.py` runs a deterministic, keyword/pattern-based crisis check on
  **every** user message, before any LLM sub-agent runs — this is
  intentionally not model-dependent, so it can't be reasoned or prompted
  out of firing, and costs no API call.
- Crisis response text (including emergency numbers) is hardcoded in
  `security.py`, not generated by an LLM, so it can't be hallucinated.
  Currently set to India Emergency (112) — would need localization for
  broader deployment.

## Setup

```bash
git clone <your-repo-url>
cd MINDGUARD-AI
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Get a free API key from https://aistudio.google.com/apikey
# Create a .env file in the project root:
echo GOOGLE_API_KEY=your-key-here > .env

# CLI version
python main.py

# Or the Streamlit chat interface
streamlit run streamlit_app.py
```

No paid APIs required — Gemini's free tier covers demo-scale usage.

## Repo structure

```
MINDGUARD-AI/
├── agents/
│   ├── checkin_agent.py     # Sub-agent 1: collects mood/stress/sleep/energy
│   ├── analysis_agent.py    # Sub-agent 2: risk scoring + trend detection
│   ├── response_agent.py    # Sub-agent 3: empathetic reflection, MCP tool calls
│   ├── resource_agent.py    # Sub-agent 4: coping resources, HIGH-risk only
│   └── root_agent.py        # Custom BaseAgent orchestrator, wires 1-4
├── memory/
│   └── mood_store.py        # Persistent JSON mood history per user
├── mcp_server/
│   ├── server.py            # FastMCP server exposing wellness tools
│   └── wellness_tools.py    # Deterministic, rule-based wellness content
├── security.py               # Deterministic crisis-language safety check
├── streamlit_app.py          # Chat UI (calming green theme, mood history sidebar)
├── style.css                 # Streamlit theme
├── main.py                   # CLI entrypoint
├── requirements.txt
└── README.md
```

## Roadmap (post-submission)

Planning a full-stack rebuild with FastAPI, React, and MongoDB Atlas to turn
this into a deployed, portfolio-ready app beyond the Kaggle capstone scope.
