import vertexai
from vertexai.preview.reasoning_engines import AdkApp
import asyncio
from vertexai import agent_engines
from personal_clone.agent import root_agent

from dotenv import load_dotenv

load_dotenv("personal_clone/.env")
import os

agent_engine_id = "2225697407641845760"
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "")
GOOGLE_CLOUD_STORAGE_BUCKET = os.environ.get("GOOGLE_CLOUD_STORAGE_BUCKET", "")

vertexai.init(
    project=GOOGLE_CLOUD_PROJECT,
    location=GOOGLE_CLOUD_LOCATION,
    staging_bucket=GOOGLE_CLOUD_STORAGE_BUCKET,
)

client = vertexai.Client()  # type: ignore

agent_engine = client.agent_engines.get(
    name="projects/personal-clone-464511/locations/us-central1/reasoningEngines/2225697407641845760"
)


async def call_agent(query, session, user_id):
    async for event in agent_engine.async_stream_query(
        user_id=user_id,
        session_id=session.get("id"),
        # session_id = session,
        message=query,
    ):
        print(event)
        print("#" * 20)

    client.agent_engines.memories.generate(
        name="projects/personal-clone-464511/locations/us-central1/reasoningEngines/2225697407641845760",
        vertex_session_source={
            "session": f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{agent_engine_id}/sessions/{session["id"]}'
        },
    )

    # await client.agent_engines.generate_memories(
    #     name="projects/personal-clone-464511/locations/us-central1/reasoningEngines/2225697407641845760",
    #     vertex_session_source={
    #         "session": f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{agent_engine_id}/sessions/{session["id"]}'
    #         }
    # )
    print("Session added to memory")


async def main():
    # session = asyncio.run(agent_engine.async_create_session(user_id="USER_ID"))
    # print("Session ID: ", session)

    session = await agent_engine.async_get_session(
        session_id="1789003824682237952", user_id="USER_ID"
    )
    # print(f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{agent_engine_id}/sessions/{session["id"]}')
    while True:
        input_text = input("You: ")
        if input_text.lower() in ["exit", "quit"]:
            break
        await call_agent(input_text, session=session, user_id="USER_ID")


if __name__ == "__main__":
    asyncio.run(main())
