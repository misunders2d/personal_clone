import vertexai
from vertexai.preview.reasoning_engines import AdkApp
import asyncio
from vertexai import agent_engines
from personal_clone.agent import root_agent

from dotenv import load_dotenv

load_dotenv("personal_clone/.env")
import os

agent_engine_id = "303645529173131264"
USER_ID = "sergey@mellanni.com"
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "")
GOOGLE_CLOUD_STORAGE_BUCKET = os.environ.get("GOOGLE_CLOUD_STORAGE_BUCKET", "")

vertexai.init(
    project=GOOGLE_CLOUD_PROJECT,
    location=GOOGLE_CLOUD_LOCATION,
    staging_bucket=GOOGLE_CLOUD_STORAGE_BUCKET,
)

# client = vertexai.Client()  # type: ignore

# agent_engine = client.agent_engines.get(
#     name=f"projects/personal-clone-464511/locations/us-central1/reasoningEngines/{agent_engine_id}"
# )


agent_engine = agent_engines.get(
    resource_name=f"projects/personal-clone-464511/locations/us-central1/reasoningEngines/{agent_engine_id}"
)


# for item in agent_engine.operation_schemas():
#     print(item, end="\n\n")


async def call_agent(query, session, user_id):

    async for event in agent_engine.async_stream_query(
        user_id=user_id,
        session_id=session.get("id"),
        message=query,
    ):
        if (
            "content" in event
            and event["content"]
            and "parts" in event["content"]
            and event["content"]["parts"]
            and event["content"]["parts"][0]
            and "text" in event["content"]["parts"][0]
        ):
            final_response = event["content"]["parts"][0]["text"]
            print("Agent Response: ", final_response)


async def main():
    session = agent_engine.create_session(user_id=USER_ID)
    print("Session ID: ", session)

    session = agent_engine.get_session(  # type: ignore
        session_id=session["id"], user_id=USER_ID
    )
    while True:
        input_text = input("You: ")
        if input_text.lower() in ["exit", "quit"]:
            break
        await call_agent(input_text, session=session, user_id=USER_ID)

    agent_engine.delete_session(session_id=session["id"], user_id=USER_ID)


if __name__ == "__main__":
    asyncio.run(main())
