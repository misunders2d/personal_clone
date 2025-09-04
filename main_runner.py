from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import VertexAiSessionService, InMemorySessionService
from google.adk import Runner
from google.genai import types
from personal_clone.agent import root_agent
import os
import asyncio
from dotenv import load_dotenv

load_dotenv('personal_clone/.env')

agent_engine_id = os.environ.get("MEMORY_BANK_ID","")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "")

app_name = "personal_clone_app"
current_session = ''

async def run_agent(query: str, user_id: str, session_id: str = current_session):
    global current_session
    memory_service = VertexAiMemoryBankService(
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
        agent_engine_id=agent_engine_id,
    )

    session_service = VertexAiSessionService(
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION,
        agent_engine_id=agent_engine_id,
        )

    if not current_session:
        session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
        current_session = session.id
    else:
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=current_session)

    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
        memory_service=memory_service
        )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=current_session,
        new_message=types.Content(role="user", parts=[types.Part(text=query)]),
        ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print("Agent Response: ", final_response)
    if session:
        await memory_service.add_session_to_memory(session=session)
        print("Session added to memory")


async def main():
    user_id = "sergey@mellanni.com"
    while True:
        query = input("Enter your question (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        await run_agent(query, user_id)


if __name__ == "__main__":
    asyncio.run(main())