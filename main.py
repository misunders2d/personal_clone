
import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Define a simple agent for demonstration
def get_time():
    import datetime
    return {"time": str(datetime.datetime.now())}

time_agent = Agent(
    name="time_agent",
    model="gemini-1.5-flash",
    description="An agent that can tell the current time.",
    instruction="You are a helpful agent that can tell the current time.",
    tools=[get_time],
)

async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=time_agent,
        app_name="my_app",
        session_service=session_service,
    )
    session = await session_service.create_session(app_name="my_app", user_id="user1")

    print("Agentic system started. Type 'exit' to quit.")
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() == "exit":
                break

            content = types.Content(role="user", parts=[types.Part(text=user_input)])
            async for event in runner.run_async(
                session_id=session.id, user_id=session.user_id, new_message=content
            ):
                print(f"Event: {event}")

        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    asyncio.run(main())
