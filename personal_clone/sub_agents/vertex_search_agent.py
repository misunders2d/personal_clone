from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool
from pydantic import BaseModel, Field

import os

GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
VERTEX_DATASTORE_ID = os.environ["VERTEX_DATASTORE_ID"]
DATASTORE_ID = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/us/collections/default_collection/dataStores/{VERTEX_DATASTORE_ID}"

vertex_toolset = VertexAiSearchTool(data_store_id=DATASTORE_ID)


class VertexMemoryOutput(BaseModel):
    topic: str = Field(description="The main topic of the memory, i.e. `Google ADK`")
    memory: str = Field(description="The actual contents of the memory")


vertex_search_agent = Agent(
    name="vertex_search_agent",
    model="gemini-2.0-flash",
    instruction="Answer questions using Vertex AI Search to find information from internal documents and notebooks. Always cite sources when available.",
    description="A Vertex AI vector search agent with access to document datastores, containing necessary information.",
    tools=[vertex_toolset],
    # include_contents="none",
    # output_schema=VertexMemoryOutput,
    output_key="vertex_search",
)
