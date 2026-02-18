import uuid

from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig, ResumabilityConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.artifacts import GcsArtifactService
from google.adk.plugins import ReflectAndRetryToolPlugin
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types

from personal_clone import agent, config

session_service = DatabaseSessionService(
    db_url="sqlite+aiosqlite:///sessions_runner.db"
)

artifact_service = GcsArtifactService(bucket_name=config.GOOGLE_CLOUD_ARTIFACT_BUCKET)


async def create_app() -> App:
    app = App(
        name=config.APP_NAME,
        root_agent=agent.root_agent,
        plugins=[ReflectAndRetryToolPlugin()],
        events_compaction_config=EventsCompactionConfig(
            summarizer=LlmEventSummarizer(llm=config.LITE_MODEL),
            compaction_interval=20,
            overlap_size=3,
        ),
        context_cache_config=ContextCacheConfig(cache_intervals=10, min_tokens=3600),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    return app


async def create_runner() -> Runner:
    runner = Runner(
        app=await create_app(),
        # agent=agent.root_agent,
        # app_name=config.APP_NAME,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    return runner


async def get_or_create_session(
    user_id, session_id=None, app_name=config.APP_NAME
) -> dict:
    try:
        if not session_id:
            sessions = await session_service.list_sessions(
                app_name=app_name, user_id=user_id
            )
            if sessions.sessions:
                return {"status": "success", "session": sessions.sessions[-1]}
            else:
                session = await session_service.create_session(
                    app_name=app_name, user_id=user_id
                )
                return {"status": "success", "session": session}

        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name=app_name, user_id=user_id
            )
        return {"status": "success", "session": session}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def delete_session(user_id, session_id, app_name=config.APP_NAME):
    await session_service.delete_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )


async def format_message_content(
    message: dict, user_id: str, session_id: str
) -> types.Content:
    parts = []
    if "text" in message:
        parts.append(types.Part(text=message.get("text")))
    if "file_data" in message:
        file_data = message["file_data"]
        file_uri = file_data.get("file_uri")
        mime_type = file_data.get("mime_type")
        ext = mime_type.split("/")[-1] if mime_type else "bin"
        display_name = file_data.get("display_name", f"{uuid.uuid4()}.{ext}")

        parts.append(
            types.Part(
                file_data=types.FileData(
                    display_name=display_name, file_uri=file_uri, mime_type=mime_type
                )
            )
        )
    if "inline_data" in message:
        inline_data = message["inline_data"]
        data = inline_data.get("data")
        mime_type = inline_data.get("mime_type")
        ext = mime_type.split("/")[-1] if mime_type else "bin"
        display_name = inline_data.get("display_name", f"{uuid.uuid4()}.{ext}")

        artifact = types.Part(
            inline_data=types.Blob(
                data=data, display_name=display_name, mime_type=mime_type
            )
        )

        version = await artifact_service.save_artifact(
            app_name=config.APP_NAME,
            user_id=user_id,
            filename=display_name,
            artifact=artifact,
            session_id=session_id,
        )

        artifact_part = await artifact_service.load_artifact(
            app_name=config.APP_NAME,
            user_id=user_id,
            filename=display_name,
            session_id=session_id,
            version=version,
        )

        parts.append(artifact_part)

    return types.Content(parts=parts, role="user")


async def query_agent(
    runner: Runner,
    user_id: str,
    session_id: str,
    new_message: types.Content,
    excluded_agents: list = [],
):
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=new_message
    ):
        parts = []
        if (
            event.author not in excluded_agents
            and event.content
            and event.content.parts
        ):
            for part in event.content.parts:
                if part.text:
                    parts.append(part.text)
        for part in parts:
            yield part


async def main():
    user_id = "test_user"
    session_id = "test_session"
    current_session = await get_or_create_session(
        app_name="personal_clone", user_id=user_id, session_id=session_id
    )
    if not isinstance(current_session.get("session"), Session):
        raise BaseException("Could not create or retrieve session")
    else:
        session_id = current_session["session"].id

    runner = await create_runner()
    while True:
        prompt = input("User: ")
        new_message = await format_message_content(
            message={"text": prompt}, user_id=user_id, session_id=session_id
        )
        if prompt.lower() in ["exit", "quit"]:
            break
        async for event in query_agent(
            runner=runner,
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
            excluded_agents=["answer_validator_agent"],
        ):
            print(event)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
