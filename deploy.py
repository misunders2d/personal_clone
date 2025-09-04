import os

from google.adk.memory import VertexAiMemoryBankService
import vertexai
from absl import app, flags
from personal_clone.agent import root_agent
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")

flags.DEFINE_bool("list", False, "List all agents.")
flags.DEFINE_bool("create", False, "Creates a new agent.")
flags.DEFINE_bool("create_memory_bank", False, "Creates a new engine without an agent.")
flags.DEFINE_bool("update", False, "Updates an agent.")
flags.DEFINE_bool("delete", False, "Deletes an existing agent.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete", "update"])

dotenv_path = os.path.join("personal_clone", ".env")
requirements_path = "requirements.txt"
agents_path = "personal_clone"


def create_memory_bank() -> None:
    """Creates a Vertex AI Memory Bank without an agent."""

    client = vertexai.Client(  # type: ignore
        project=(
            FLAGS.project_id if FLAGS.project_id else os.environ["GOOGLE_CLOUD_PROJECT"]
        ),
        location=(
            FLAGS.location if FLAGS.location else os.environ["GOOGLE_CLOUD_LOCATION"]
        ),
    )
    agent_engine = client.agent_engines.create()
    print(f"Created memory bank: {agent_engine.api_resource.name}")


def create() -> None:
    """Creates an agent engine for Personal Clone agent."""
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)

    remote_agent = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        requirements=requirements_path,
        extra_packages=[agents_path]
    )
    print(f"Created remote agent: {remote_agent.resource_name}")


def update(resource_id: str) -> None:
    """Updates an agent engine for Personal Clone agent."""

    def memory_bank_service_builder(
        agent_engine_id: str = resource_id,
    ) -> VertexAiMemoryBankService:
        return VertexAiMemoryBankService(
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ["GOOGLE_CLOUD_LOCATION"],
            agent_engine_id=agent_engine_id,
        )

    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
        memory_service_builder=memory_bank_service_builder,
    )

    remote_agent = agent_engines.update(
        resource_id,
        agent_engine=adk_app,  # type: ignore
        display_name="personal_clone",
        requirements=requirements_path,
        extra_packages=[agents_path]
    )
    print(f"Updated remote agent: {remote_agent.resource_name}")


def delete(resource_id: str) -> None:
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")


def list_agents() -> None:
    remote_agents = agent_engines.list()
    template = """
{agent.name} ("{agent.display_name}")
- Create time: {agent.create_time}
- Update time: {agent.update_time}
"""
    remote_agents_string = "\n".join(
        template.format(agent=agent) for agent in remote_agents
    )
    print(f"All remote agents:\n{remote_agents_string}")


def main(argv: list[str]) -> None:
    del argv  # unused
    load_dotenv(dotenv_path)

    project_id = (
        FLAGS.project_id if FLAGS.project_id else os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    location = FLAGS.location if FLAGS.location else os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

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

    if FLAGS.list:
        list_agents()
    elif FLAGS.create:
        create()
    elif FLAGS.create_memory_bank:
        create_memory_bank()
    elif FLAGS.delete:
        if not FLAGS.resource_id:
            print("resource_id is required for delete")
            return
        delete(FLAGS.resource_id)
    elif FLAGS.update:
        if not FLAGS.resource_id:
            print("resource_id is required for update")
            return
        update(FLAGS.resource_id)
    else:
        print("Unknown command")


if __name__ == "__main__":
    app.run(main)
