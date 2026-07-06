import asyncio
import sys
import time

# Fix for Windows PowerShell: default console encoding (cp1252) can't
# print emoji, which crashes any print() containing one.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv

load_dotenv()

from agents.root_agent import root_agent

APP_NAME = "agents"
MAX_RETRIES = 4


async def main():

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id="user1"
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,  # FIXED: was "mindguard_a" — mismatched the session's
                             # app_name above, which is a landmine bug even if
                             # InMemorySessionService tolerated it silently.
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

        # Retry loop handles BOTH 429 (rate limit) and 503 (server
        # overloaded) instead of just 429, since 503 can also happen
        # mid-conversation and previously crashed the whole loop.
        for attempt in range(MAX_RETRIES):
            try:
                async for event in runner.run_async(
                    user_id="user1",
                    session_id=session.id,
                    new_message=message
                ):
                    if event.content and event.content.parts:
                        print(event.content.parts[0].text)
                break  # success — exit retry loop

            except ClientError as e:
                code = getattr(e, "code", None)
                is_last_attempt = attempt == MAX_RETRIES - 1

                if code == 429 and not is_last_attempt:
                    wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s, 16s
                    print(f"\n[Rate limit reached — waiting {wait_time}s, then retrying automatically...]")
                    time.sleep(wait_time)
                    continue

                if code == 503 and not is_last_attempt:
                    wait_time = 4 + (attempt * 3)  # 4s, 7s, 10s, 13s
                    print(f"\n[Google's servers are busy — waiting {wait_time}s, then retrying automatically...]")
                    time.sleep(wait_time)
                    continue

                # Ran out of retries, or a different kind of error entirely
                if code == 429:
                    print(
                        "\n[Rate limit reached -- free tier allows a handful of "
                        "requests per minute. Wait about 30-60 seconds, then "
                        "just type your last answer again.]"
                    )
                elif code == 503:
                    print(
                        "\n[Google's servers are experiencing high demand, even "
                        "after several retries. Please wait a minute and try again.]"
                    )
                else:
                    raise
                break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMindGuard AI: Take care! See you next time. 💙")