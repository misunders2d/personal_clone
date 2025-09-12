import os
import asyncio

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from google.adk.memory import VertexAiMemoryBankService, InMemoryMemoryService


dotenv_path = os.path.join("personal_clone", ".env")

FLAGS = flags.FLAGS

flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string(
    "resource_id",
    None,
    "ReasoningEngine resource ID (returned after deploying the agent)",
)
flags.DEFINE_string("user_id", None, "User ID (can be any string).")
flags.mark_flag_as_required("resource_id")
flags.mark_flag_as_required("user_id")


def main(argv: list[str]) -> None:  # pylint: disable=unused-argument

    load_dotenv(dotenv_path)

    project_id = (
        FLAGS.project_id if FLAGS.project_id else os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    location = FLAGS.location if FLAGS.location else os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    if not project_id:
        print("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    elif not location:
        print("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    elif not bucket:
        print("Missing required environment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=bucket,
    )

    # memory_service = VertexAiMemoryBankService(
    #     project=project_id, location=location, agent_engine_id=FLAGS.resource_id
    # )
    # memory_service = InMemoryMemoryService()

    agent = agent_engines.get(FLAGS.resource_id)
    print(f"Found agent with resource ID: {FLAGS.resource_id}")
    session = agent.create_session(user_id=FLAGS.user_id)  # type: ignore
    print(f"Created session for user ID: {FLAGS.user_id}")
    print("Type 'quit' to exit.")
    while True:
        user_input = input("Input: ")
        if user_input == "quit":
            break

        for event in agent.stream_query(  # type: ignore
            user_id=FLAGS.user_id, session_id=session["id"], message=user_input
        ):
            if event["author"] in (
                "memory_recall_agent",
                "vertex_recall_agent",
                "answer_validator_agent",
            ):
                pass
            elif "content" in event:
                if "parts" in event["content"]:
                    parts = event["content"]["parts"]
                    for part in parts:
                        if "text" in part:
                            text_part = part["text"]
                            print(f"Response: {text_part}")

        # if "events" in session and len(session["events"]) > 0:
        #     asyncio.run(memory_service.add_session_to_memory(session))
        #     print(f"✅ Session {session["id"]} automatically saved to memory bank")

    agent.delete_session(user_id=FLAGS.user_id, session_id=session["id"])  # type: ignore
    print(f"Deleted session for user ID: {FLAGS.user_id}")


if __name__ == "__main__":
    app.run(main)
