from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool

from .. import config


vertex_toolset = VertexAiSearchTool(data_store_id=config.DATASTORE_ID)


def create_vertex_search_agent(
    name="vertex_search_agent", output_key="vertex_search"
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
        If you are unable to find relevant information, reply with a "PASS", nothing else.
        If the user is requesting to add or modify a record, reply with "PASS", nothing else.
        <EXTREMELY IMPORTANT!!!>
            - You are a read-only agent, do not attempt to use write mode.
            - Use EXACT user input to search memories, don't come up with anythign on yourself.
            - You are ONLY allowed to output "PASS" or search results starting with "VERTEX SEARCH RESULTS:" and ending with "VERTEX SEARCH RESULTS END", NOTHING ELSE!
            - If the user's request implies updating or modifying memories, just output "PASS".
            - Your ONLY mode of operation is SEARCHING MEMORIES, anythign beyond that automatically implies "PASS"!
        </EXTREMELY IMPORTANT!!!>

        """,
        tools=[vertex_toolset],
        output_key=output_key,
    )
    return vertex_search_agent
