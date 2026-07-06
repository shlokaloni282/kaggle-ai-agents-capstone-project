"""
Root Orchestrator
-------------------
Replaces the plain SequentialAgent. SequentialAgent runs every sub-agent
back-to-back on every call to runner.run_async() -- i.e. on every single
user message -- with no way to say "check-in isn't finished, stop here."
That's what was causing analysis_agent/response_agent/resource_agent to
fire (and burn API quota) before the user had even answered all the
check-in questions.

This custom BaseAgent runs checkin_agent every turn, but only continues to
analysis -> response -> resource once checkin_agent itself signals
completion via the CHECKIN_COMPLETE marker (see checkin_agent.py).
"""

"""from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from agents.checkin_agent import checkin_agent
from agents.analysis_agent import analysis_agent
from agents.response_agent import response_agent
from agents.resource_agent import resource_agent

COMPLETE_MARKER = "CHECKIN_COMPLETE"


class MindGuardRootAgent(BaseAgent):

    checkin_agent: BaseAgent
    analysis_agent: BaseAgent
    response_agent: BaseAgent
    resource_agent: BaseAgent

    def __init__(self, name: str = "mindguard_pipeline"):
        super().__init__(
            name=name,
            checkin_agent=checkin_agent,
            analysis_agent=analysis_agent,
            response_agent=response_agent,
            resource_agent=resource_agent,
            sub_agents=[checkin_agent, analysis_agent, response_agent, resource_agent],
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Always run check-in for this turn. It either asks the next
        #    missing question, or (once complete) emits CHECKIN_COMPLETE.
        checkin_done = False
        async for event in self.checkin_agent.run_async(ctx):
            yield event
            if event.content and event.content.parts:
                text = event.content.parts[0].text or ""
                if COMPLETE_MARKER in text:
                    checkin_done = True

        # 2. Not finished yet -> stop here and wait for the user's next
        #    answer. Do NOT run analysis/response/resource on partial data.
        if not checkin_done:
            return

        # 3. Check-in complete -> run the rest of the pipeline once.
        async for event in self.analysis_agent.run_async(ctx):
            yield event

        async for event in self.response_agent.run_async(ctx):
            yield event

        async for event in self.resource_agent.run_async(ctx):
            yield event


root_agent = MindGuardRootAgent()"""
"""
Root Orchestrator
-------------------
Custom BaseAgent (not SequentialAgent) because two things need branching
logic that a plain sequential pipeline can't express:

1. Don't run analysis/response/resource until check-in is actually
   complete (SequentialAgent has no concept of "wait for the user").
2. Only run resource_agent (which does a real Google Search) when risk is
   HIGH -- running it every time wastes API calls and doesn't match what
   the feature is for.

Also handles: saving each completed check-in to persistent memory, and
injecting the user's recent history into analysis_agent's state so it can
detect multi-day trends, not just judge a single day in isolation.
"""

import json
import re
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from agents.checkin_agent import checkin_agent
from agents.analysis_agent import analysis_agent
from agents.response_agent import response_agent
from agents.resource_agent import resource_agent

try:
    from memory.mood_store import add_entry, get_recent_history_summary
except ModuleNotFoundError:
    from ..memory.mood_store import add_entry, get_recent_history_summary

COMPLETE_MARKER = "CHECKIN_COMPLETE"


class MindGuardRootAgent(BaseAgent):

    checkin_agent: BaseAgent
    analysis_agent: BaseAgent
    response_agent: BaseAgent
    resource_agent: BaseAgent

    def __init__(self, name: str = "mindguard_pipeline"):
        super().__init__(
            name=name,
            checkin_agent=checkin_agent,
            analysis_agent=analysis_agent,
            response_agent=response_agent,
            resource_agent=resource_agent,
            sub_agents=[checkin_agent, analysis_agent, response_agent, resource_agent],
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        user_id = ctx.session.user_id

        # 1. Run check-in for this turn.
        checkin_done = False
        checkin_text = ""
        async for event in self.checkin_agent.run_async(ctx):
            yield event
            if event.content and event.content.parts:
                text = event.content.parts[0].text or ""
                checkin_text += text
                if COMPLETE_MARKER in text:
                    checkin_done = True

        if not checkin_done:
            return  # wait for the user's next answer

        # 2. Parse the JSON the check-in agent emitted after CHECKIN_COMPLETE.
        try:
            json_str = checkin_text.split(COMPLETE_MARKER, 1)[1]
            start, end = json_str.index("{"), json_str.rindex("}") + 1
            checkin_data = json.loads(json_str[start:end])
            add_entry(user_id, checkin_data)
        except (ValueError, json.JSONDecodeError, IndexError):
            checkin_data = {}

        # 3. Inject recent mood history into state so analysis_agent's
        #    {mood_history} template placeholder has real data.
        ctx.session.state["mood_history"] = get_recent_history_summary(user_id)

        # 4. Run analysis.
        analysis_text = ""
        async for event in self.analysis_agent.run_async(ctx):
            yield event
            if event.content and event.content.parts:
                analysis_text += event.content.parts[0].text or ""

        # 5. Run the supportive response (always).
        async for event in self.response_agent.run_async(ctx):
            yield event

        # 6. Only run the Google-Search-backed resource agent if risk is HIGH.
        risk_match = re.search(r"RISK LEVEL:\s*\n?\s*(LOW|MEDIUM|HIGH)", analysis_text, re.IGNORECASE)
        risk_level = risk_match.group(1).upper() if risk_match else None

        if risk_level == "HIGH":
            async for event in self.resource_agent.run_async(ctx):
                yield event


root_agent = MindGuardRootAgent()