# MindGuard AI 🌿💚

**A multi-agent mental wellness companion for India's silent mental health crisis.**

Daily AI-powered check-ins that catch early burnout and stress patterns before they escalate — built with Google ADK, Gemini, and MCP.

> Built for the Kaggle "AI Agents: Intensive Vibe Coding" Capstone — **Track: Agents for Good**

---

## Why this exists

Roughly 1 in 5 people in India experience a mental health condition, and close to 80% of them never seek help. MindGuard AI isn't therapy and it isn't diagnosis — it's the small, private, judgment-free moment of "how am I actually doing today" that most people never carve out time for.

Every day, it asks a handful of short questions about mood, stress, sleep, and energy. It remembers your answers across days, not just today's, because burnout shows up as a trend, not a single bad day. If things look fine, you get a supportive reflection and practical coping resources. If the pattern looks genuinely concerning, it surfaces search-backed support resources — and separately, a hard-coded safety net catches crisis language the moment it's typed, regardless of risk level.

## Architecture

```
User Input
    │
    ▼
MindGuardRootAgent (custom orchestrator, subclasses BaseAgent)
    │
    ├── 0. Deterministic safety_check() (security.py) — runs on
    │      EVERY message, before any LLM call. Regex-based crisis
    │      language detection. If triggered, responds immediately
    │      with a hard-coded safety_response() (incl. India
    │      Emergency: 112) and stops the pipeline for that turn.
    │      This can't be reasoned around by prompt phrasing, and
    │      costs no API call.
    │
    ├── 1. CheckInAgent — asks the daily questions one at a time,
    │      waits until all four are answered before letting the
    │      pipeline continue (signals via a CHECKIN_COMPLETE marker)
    │
    ├── 2. AnalysisAgent — pulls recent mood history from memory,
    │      scores risk (LOW / MEDIUM / HIGH) based on today's answers
    │      plus multi-day trends, not just a single check-in
    │
    ├── 3. ResponseAgent — writes a warm, personalized reflection,
    │      and can call wellness tools (breathing exercises,
    │      grounding, journaling prompts, etc.) via MCP instead of
    │      generating them freeform
    │
    └── 4. ResourceAgent — only runs if risk is HIGH; recommends
           coping resources and, when appropriate, professional/
           emergency support framing
    │
    ▼
Persistent memory (memory/mood_store.py) — saves every completed
check-in as JSON so tomorrow's agent isn't starting from zero
```

### Why a custom orchestrator, not `SequentialAgent`

The first version used ADK's `SequentialAgent`, which runs every sub-agent in order regardless of state. That meant analysis, response, and even the resource-search agent could fire before the check-in was actually complete — burning API calls on incomplete data and producing confusing output.

The fix was subclassing `BaseAgent` directly (`agents/root_agent.py`) to control the flow explicitly: don't move past check-in until it signals completion via `CHECKIN_COMPLETE`, and don't run the resource agent unless analysis actually reports HIGH risk. This was the single biggest design decision in the project, and it came from hitting that wall during testing, not from planning it upfront.

## Key concepts demonstrated

| Concept | Where | How |
|---|---|---|
| **Multi-agent system (ADK)** | `agents/` | Four specialized `Agent` instances (CheckIn, Analysis, Response, Resource) coordinated by a custom `BaseAgent` orchestrator (`root_agent.py`) |
| **MCP Server** | `mcp_server/` | `server.py` (FastMCP over stdio) exposes deterministic, rule-based wellness tools from `wellness_tools.py` — breathing exercises, grounding activities, journal prompts, affirmations, sleep tips — which `response_agent` can call instead of generating them freeform |
| **Deterministic safety layer** | `security.py` | Regex/keyword-based crisis language detection that runs on every user message before any LLM sub-agent executes. Model-independent by design, so it can't be talked out of firing, and costs no API call |
| **Sessions & long-term memory** | `memory/mood_store.py` | JSON-backed persistent check-in history per user, surviving process restarts (unlike `InMemorySessionService` alone), enabling `AnalysisAgent` to detect multi-day trends |
| **Conditional branching** | `agents/root_agent.py` | Orchestrator gates the pipeline on check-in completion, and only invokes `ResourceAgent` when risk is HIGH — rather than running every agent on every turn |
| **Deployability** | `streamlit_app.py`, `mcp_server/` | Same agent core runs as a local Streamlit web app and as a local stdio-based MCP server, with no changes to the underlying agent logic |

## Project structure

```
MINDGUARD-AI/
├── agents/
│   ├── root_agent.py        # Custom BaseAgent orchestrator
│   ├── checkin_agent.py     # Daily check-in questions
│   ├── analysis_agent.py    # Risk scoring + trend analysis
│   ├── response_agent.py    # Warm, personalized replies + MCP tool calls
│   └── resource_agent.py    # Coping resources (HIGH risk gets extra framing)
├── mcp_server/
│   ├── server.py             # MCP server over stdio (FastMCP)
│   └── wellness_tools.py     # Deterministic wellness tools exposed via MCP
├── memory/
│   └── mood_store.py         # Persistent JSON-backed check-in history
├── security.py                # Deterministic crisis-language safety check
├── main.py                    # Terminal entry point
├── streamlit_app.py            # Streamlit UI (calming mint-green theme)
├── style.css
├── requirements.txt
└── .gitignore
```

## Getting started

### 1. Clone and set up a virtual environment

```bash
git clone https://github.com/shlokaloni282/kaggle-ai-agents-capstone-project.git
cd kaggle-ai-agents-capstone-project/MINDGUARD-AI
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_key_here
```

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run it

**Terminal version** (fastest for trying it out):
```bash
python main.py
```

**Streamlit web app**:
```bash
streamlit run streamlit_app.py
```

The MCP server (`mcp_server/server.py`) doesn't need to be run separately —
`response_agent.py` spawns it automatically as a stdio subprocess using the
same Python interpreter, the moment the agent needs a wellness tool.

## Limitations & What's Next

This is **not a diagnostic tool**. The risk scoring reflects the LLM's judgment guided by prompt instructions, not a validated clinical implementation. Before anyone outside a personal or educational context uses this, a qualified mental health professional should review the response logic.

Upcoming features:

- Named, verified Indian helplines (iCall, Vandrevala Foundation, KIRAN) alongside the current emergency number in the safety response
- Cloud-based persistent memory (currently a local JSON file tied to one machine)
- A mobile-friendly interface, since this is such a personal, on-the-go use case
- With explicit user consent, an optional way to notify a trusted contact if risk remains high for several consecutive days
- Finding nearby licensed therapists and counselors based on the user's location, with the user's permission

##Demo Video(YT): https://youtu.be/HFeeNHSrJBg?si=mQ81WRrEzGYBWKIz

## Built with

Python · Google ADK · Gemini 2.5 Flash-Lite · Model Context Protocol (MCP) · Streamlit

---

*Built for the Kaggle "5 Day AI Agents: Intensive Vibe Coding" Capstone — Track: Agents for Good.*
