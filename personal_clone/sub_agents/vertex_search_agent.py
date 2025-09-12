from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool
from pydantic import BaseModel, Field

import os
from dotenv import load_dotenv

dotenv_file_path = os.path.abspath(os.path.join(__file__, os.pardir, ".env"))
load_dotenv()


GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
# GOOGLE_CLOUD_PROJECT = 1047411111083
GOOGLE_CLOUD_LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
VERTEX_DATASTORE_ID = os.environ["VERTEX_DATASTORE_ID"]
DATASTORE_ID = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/global/collections/default_collection/dataStores/{VERTEX_DATASTORE_ID}"
DATASTORE_ID = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/global/collections/default_collection/dataStores/documents"  # documents
vertex_toolset = VertexAiSearchTool(data_store_id=DATASTORE_ID)


class VertexMemoryOutput(BaseModel):
    topic: str = Field(description="The main topic of the memory, i.e. `Google ADK`")
    memory: str = Field(description="The actual contents of the memory")


def create_vertex_search_agent(
    name="vertex_search_agent",
    output_schema: type[BaseModel] | None = None,
    output_key: str | None = None,
) -> Agent:
    vertex_search_agent = Agent(
        name=name,
        model="gemini-2.0-flash",
        description="A Vertex AI vector search agent with access to document datastores, containing necessary information.",
        instruction="""
        Answer user questions and fetch relevant data based on user's input using Vertex AI Search to find information from internal documents and notebooks.
        Always use exact user input as a query for your vertex_toolset.
        Always cite sources when available.
        You are designed to fetch knowledge only (read-only mode), ignore all other requests that require updating or deleting memories.
        If you are unable to find relevant information, reply with a short "INFORMATION NOT FOUND", nothing else.
        """,
        tools=[vertex_toolset],
        # include_contents="none",
        output_schema=output_schema,
        output_key=output_key,
    )
    return vertex_search_agent
