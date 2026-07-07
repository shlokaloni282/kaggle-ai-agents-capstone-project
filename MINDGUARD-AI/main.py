import asyncio
import sys

# Fix for Windows PowerShell: default console encoding (cp1252) can't
# print emoji, which crashes any print() containing one.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import APIError, ClientError
from dotenv import load_dotenv

load_dotenv()

from agents.root_agent import root_agent

APP_NAME = "agents"  # matches streamlit_app.py exactly — no mismatch


async def main():

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id="user1"
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,  # same constant used above — no drift
        session_service=session_service
    )

    print("🌱 MindGuard AI Started")
    print("Type exit to quit")

    while True:

        try:
            user_input = input("\nYou: ")
        except EOFError:
            print("\nMindGuard AI: Take care! See you next time. 💙")
            break

        if user_input.lower() == "exit":
            break

        message = types.Content(
            role="user",
            parts=[
                types.Part(text=user_input)
            ]
        )

        print("\n🌱MindGuard AI:")

        try:
            async for event in runner.run_async(
                user_id="user1",
                session_id=session.id,
                new_message=message
            ):
                if event.content and event.content.parts:
                    print(event.content.parts[0].text)

        except ClientError as e:
            code = getattr(e, "code", None)
            if code == 429:
                print(
                    "\n[Rate limit reached -- free tier allows a handful of "
                    "requests per minute. Wait about 30-60 seconds, then "
                    "just type your last answer again.]"
                )
            elif code == 503:
                print(
                    "\n[Google's servers are experiencing high demand right now. "
                    "Wait a moment and try again.]"
                )
            else:
                raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMindGuard AI: Take care! See you next time. 💙")