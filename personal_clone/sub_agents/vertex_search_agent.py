from google.adk.agents import Agent
from google.adk.tools.vertex_ai_search_tool import VertexAiSearchTool


import os

GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
VERTEX_DATASTORE_ID = os.environ["VERTEX_DATASTORE_ID"]


DATASTORE_ID = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/us/collections/default_collection/dataStores/{VERTEX_DATASTORE_ID}"


vertex_toolset = VertexAiSearchTool(data_store_id=DATASTORE_ID)


vertex_search_agent = Agent(
    name="vertex_search_agent",
    model="gemini-2.5-flash",
    instruction="Answer questions using Vertex AI Search to find information from internal documents. Always cite sources when available.",
    description="Enterprise document search assistant with Vertex AI Search capabilities",
    tools=[vertex_toolset],
)
