from google.adk.artifacts import GcsArtifactService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types

from personal_clone import agent, config

session_service = DatabaseSessionService(
    db_url="sqlite+aiosqlite:///sessions_runner.db"
)
artifact_service = GcsArtifactService(bucket_name=config.GOOGLE_CLOUD_ARTIFACT_BUCKET)


async def create_runner() -> Runner:
    runner = Runner(
        agent=agent.root_agent,
        app_name=config.APP_NAME,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    return runner


async def get_or_create_session(user_id, session_id=None, app_name=config.APP_NAME):
    if not session_id:
        sessions = await session_service.list_sessions(
            app_name=app_name, user_id=user_id
        )
        if sessions.sessions:
            return sessions.sessions[-1]
        else:
            session = await session_service.create_session(
                app_name=app_name, user_id=user_id
            )
            return session

    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        session = await session_service.create_session(
            app_name=app_name, user_id=user_id
        )
    return session


async def delete_session(user_id, session_id, app_name=config.APP_NAME):
    await session_service.delete_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )


def format_messaage_content(message: dict) -> types.Content:
    parts = []
    if "text" in message:
        parts.append(types.Part(text=message["text"]))
    if "image_url" in message:
        parts.append(types.Part(image_url=message["image_url"]))
    if "file_url" in message:
        parts.append(types.Part(file_url=message["file_url"]))
    return types.Content(parts=parts, role="user")


async def query_agent(
    runner: Runner, user_id: str, session_id: str, new_message: types.Content
):
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=new_message
    ):
        yield event


# if __name__ == "__main__":
#     user_id = "test_user"
#     session_id="test_session"
#     session_id = await get_or_create_session(app_name="personal_clone", user_id=user_id, session_id=session_id).id

#     while True:
#         prompt = input("User: ")
#         new_message = types.Content(parts = [types.Part(text = prompt)], role = "user")
#         if prompt.lower() in ["exit", "quit"]:
#             break
#         for event in runner.run(user_id=user_id, session_id=session_id, new_message = new_message):
#             print(event)
