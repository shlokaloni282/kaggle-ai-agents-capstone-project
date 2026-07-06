# MindGuard AI 🧠💚

**A multi-agent mental wellness companion for India's silent mental health crisis.**

Daily AI-powered check-ins that catch early burnout and anxiety before they escalate — built with Google ADK, Gemini, and MCP.

> Built for the Kaggle "AI Agents: Intensive Vibe Coding" Capstone — **Track: Agents for Good**

---

## Why this exists

Roughly 1 in 5 people in India experience a mental health condition, and close to 80% of them never seek help. MindGuard AI isn't therapy and it isn't diagnosis — it's the small, private, judgment-free moment of "how am I actually doing today" that most people never carve out time for.

Every day, it asks a handful of short questions about mood, stress, sleep, and energy — loosely inspired by PHQ-2 and GAD-2, the same short screening tools used in real clinical settings (this is **not** a clinical implementation, just inspired by the same logic). It remembers your answers across days, not just today's, because burnout shows up as a trend, not a single bad day. If things look fine, you get a supportive nudge. If the pattern looks genuinely concerning, it surfaces real, verified Indian helplines — iCall, Vandrevala Foundation, KIRAN.

## Architecture

```
User Input
    │
    ▼
MindGuardRootAgent (custom orchestrator, subclasses BaseAgent)
    │
    ├── 1. CheckInAgent — asks the daily questions, waits until all are
    │      answered before letting the pipeline continue
    │
    ├── 2. AnalysisAgent — pulls mood history from memory, scores risk
    │      (LOW / MEDIUM / HIGH) using PHQ-2 / GAD-2–inspired thresholds,
    │      looks at multi-day trends rather than a single check-in
    │
    ├── 3. ResponseAgent — writes a warm, personalized reply based on
    │      that risk level
    │
    └── 4. ResourceAgent — only runs if risk is HIGH; uses Google
           Search plus a hardcoded, verified list of Indian helplines
           as a safety net
    │
    ▼
Persistent memory (memory/mood_store.py) — saves every check-in so
tomorrow's agent isn't starting from zero
```

### Why a custom orchestrator, not `SequentialAgent`

The first version used ADK's `SequentialAgent`, which runs every sub-agent in order regardless of state. That meant analysis, response, and even the resource-search agent could fire before the check-in was actually complete — burning API calls on incomplete data and producing confusing output.

The fix was subclassing `BaseAgent` directly to control the flow explicitly: don't move past check-in until it signals completion, and don't run resource search unless risk is actually high. This was the single biggest design decision in the project, and it came from hitting that wall during testing, not from planning it upfront.

## Key concepts demonstrated

| Concept | Where | How |
|---|---|---|
| **Multi-agent system (ADK)** | `agents/` | Four specialized `Agent` instances (CheckIn, Analysis, Response, Resource) coordinated by a custom `BaseAgent` orchestrator (`root_agent.py`) |
| **MCP Server** | `mcp_server/` | `server.py` + `wellness_tools.py` expose wellness tooling through the Model Context Protocol, running over stdio |
| **Security** | `security.py` | API keys loaded from environment variables, never committed to source |
| **Sessions & long-term memory** | `memory/` | `InMemorySessionService` (`session_memory.py`) for per-turn context, plus `mood_store.py` persisting check-in history to disk so trends can be tracked across days |
| **Custom tools** | `tools/` | A `FunctionTool`-based risk scorer applying fixed, explainable thresholds rather than leaving something this sensitive to free-form LLM judgment |
| **Deployability** | `streamlit_app.py`, `mcp_server/` | Same agent core runs as a local Streamlit web app and as a local stdio-based MCP server, with no changes to the underlying logic |

## Project structure

```
MINDGUARD-AI/
├── agents/
│   ├── root_agent.py        # Custom BaseAgent orchestrator
│   ├── checkin_agent.py     # Daily check-in questions
│   ├── analysis_agent.py    # Risk scoring + trend analysis
│   ├── response_agent.py    # Warm, personalized replies
│   └── resource_agent.py    # Helpline lookup (HIGH risk only)
├── mcp_server/
│   ├── server.py             # MCP server over stdio
│   └── wellness_tools.py     # Wellness tools exposed via MCP
├── memory/
│   ├── mood_store.py         # Persistent JSON-backed check-in history
│   └── session_memory.py     # InMemorySessionService wrapper
├── tools/
│   └── search_tool.py        # Google Search FunctionTool wrapper
├── tests/
│   └── test_agents.py
├── main.py                   # Terminal entry point
├── streamlit_app.py           # Streamlit UI (calming mint-green theme)
├── style.css
├── security.py                # Env-based key handling
├── requirements.txt
└── .gitignore
```

## Getting started

### 1. Clone and set up a virtual environment

```bash
git clone https://github.com/shlokaloni282/mindguard-ai.git
cd mindguard-ai
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your API key

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
```

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).

### 3. Run it

**Terminal version** (fastest for trying it out):
```bash
python main.py
```

**Streamlit web app**:
```bash
streamlit run streamlit_app.py
```

**MCP server** (stdio):
```bash
python -m mcp_server.server
```

## Limitations & what's next

This is **not a diagnostic tool**. The risk scoring is inspired by real clinical screening tools, not a validated implementation of them. Before anyone outside a personal or educational context used this, an actual mental health professional should review the thresholds and response logic.

Next steps on the list:
- Proper long-term memory (currently a local JSON file, tied to one machine)
- A mobile-friendly interface, since this is such a personal, on-the-go use case
- With explicit consent, an optional way to loop in a trusted contact if risk stays high for several days in a row

## Built with

Python · Google ADK · Gemini · Model Context Protocol (MCP) · Streamlit

---

*Built for the Kaggle "AI Agents: Intensive Vibe Coding" Capstone — Track: Agents for Good.*
