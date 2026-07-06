# Mental Wellness Check-in & Burnout Prevention Agent

A multi-agent system built with Google's Agent Development Kit (ADK) and
Gemini that runs a 2-minute daily mood check-in, tracks patterns over time
using PHQ-2/GAD-2 screening logic, and responds with personalized coping
strategies — escalating to verified local resources when risk is high.

**Track:** Agents for Good — Mental Health
**Course:** Kaggle 5-Day AI Agents Intensive: Vibe Coding with Google

## Problem

An estimated 1 in 5 people in India experience a mental health condition in
a given year, and the large majority never seek help — largely due to
stigma, cost, and simply not noticing early warning signs until they've
escalated. Most people don't have a low-friction, private way to notice
"I've been sleeping badly and snapping at people for 10 days straight" until
it's a crisis.

## Solution

A daily 2-minute check-in that a person can do from their phone, that quietly
builds a picture of their mood over weeks — the way a good friend would
notice a pattern — and nudges them toward a coping strategy or professional
help _before_ things escalate, not after.

## Architecture

```
                         ┌─────────────────────────┐
                         │   WellnessRootAgent      │
                         │  (custom orchestrator)   │
                         └────────────┬─────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────────┐      ┌───────────────────────┐      ┌──────────────────┐
│  1. CheckInAgent   │      │ 2. PatternAnalysis     │      │ 3. ResponseAgent │
│  (LoopAgent)       │ ───▶ │    Agent (LlmAgent)    │ ───▶ │   (LlmAgent)     │
│  asks mood Qs,     │      │  reads 7-14 day        │      │  low/mod: coping │
│  loops until       │      │  history, scores       │      │  strategy        │
│  complete           │      │  PHQ-2/GAD-2 + trend    │      │  high: gentle    │
│  (max 5 turns)     │      │  -> risk_tier           │      │  helpline nudge  │
└─────────┬──────────┘      └────────────┬────────────┘      └────────┬─────────┘
          │                              │                            │
          ▼                              ▼                            │ if risk_tier
┌───────────────────┐        ┌───────────────────────┐                │  == "high"
│  mood_store.py     │◀──────│  score_risk() tool     │                ▼
│  (JSON, per-user,  │       │  deterministic rules   │      ┌──────────────────────┐
│  persists across   │       └───────────────────────┘      │ 4. ResourceFinder     │
│  sessions/days)    │                                      │    Agent (LlmAgent)   │
└────────────────────┘                                      │  google_search tool   │
                                                              │  -> local therapists, │
                                                              │  support groups       │
                                                              └──────────────────────┘
```

To render this as an image for your Writeup, paste the block into
[mermaid.live](https://mermaid.live) using the flow above, or take a
screenshot of this ASCII diagram — either is fine for the submission.

## ADK concepts used

| Concept                           | Where                                                                                          |
| --------------------------------- | ---------------------------------------------------------------------------------------------- |
| Multi-agent system (4 sub-agents) | `agents/`                                                                                      |
| LoopAgent                         | `checkin_agent.py` — loops until all mood fields are captured                                  |
| Custom orchestrator (BaseAgent)   | `root_agent.py` — conditional branching to resource finder                                     |
| Session state                     | passed via `InvocationContext.session.state` across all agents                                 |
| Long-term memory across sessions  | `memory/mood_store.py` — JSON store, survives restarts (InMemorySessionService alone does not) |
| Google Search tool                | `resource_finder_agent.py`                                                                     |
| FunctionTool                      | `score_risk`, `get_recent_history_tool`, `add_entry_tool`                                      |
| Gemini as LLM backbone            | `gemini-2.0-flash` everywhere (bonus)                                                          |

## Why LoopAgent isn't used for "daily" timing

ADK's `LoopAgent` loops sub-agents repeatedly **within a single run** — it
doesn't wait for real calendar days to pass. We use it correctly here to
re-ask incomplete check-in questions in one sitting. The actual "once a day"
cadence is a scheduling problem, not an agent problem: deploy `main.py`'s
logic behind a Cloud Run endpoint and trigger it once daily with Cloud
Scheduler (or plain cron if self-hosting). This is called out explicitly so
judges see the distinction is understood, not glossed over.

## Setup

```bash
git clone <your-repo-url>
cd mental_wellness_agent
pip install -r requirements.txt

# Get a free API key from https://aistudio.google.com/apikey
export GOOGLE_API_KEY="your-key-here"

python main.py
```

No paid APIs required — Gemini's free tier and ADK's built-in `google_search`
tool are both zero-cost for demo-scale usage.

## Deployability (bonus)

To deploy to Cloud Run:

```bash
gcloud run deploy mental-wellness-agent \
  --source . \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY \
  --allow-unauthenticated
```

Swap `memory/mood_store.py`'s JSON file for Firestore if you need durability
across container restarts in production (containers on Cloud Run are
ephemeral — local JSON files won't survive a redeploy).

## Safety notes

- The agent never diagnoses. PHQ-2/GAD-2 are validated _screening_ tools,
  not diagnostic instruments, and the prompts are written to reflect that.
- Crisis helpline numbers are hardcoded in `response_agent.py`, not
  generated by the LLM, so they can't be hallucinated. Verify they're still
  current before any real deployment.
- `ResourceFinderAgent` is instructed to only report search results it can
  verify are real and current — fewer verified resources over padded lists.

## Repo structure

```
mental_wellness_agent/
├── agents/
│   ├── checkin_agent.py          # Sub-agent 1 + LoopAgent
│   ├── pattern_analysis_agent.py # Sub-agent 2
│   ├── response_agent.py         # Sub-agent 3
│   ├── resource_finder_agent.py  # Sub-agent 4 + google_search
│   └── root_agent.py             # Custom orchestrator, wires 1-4
├── memory/
│   └── mood_store.py             # Persistent long-term memory (JSON)
├── data/                         # Per-user mood history JSON files (gitignored)
├── main.py                       # CLI entrypoint / demo runner
├── requirements.txt
└── README.md
```
