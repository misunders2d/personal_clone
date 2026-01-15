from google.adk.agents import Agent

from .. import config
from ..callbacks.before_after_agent import professional_agents_checker

# from ..callbacks.before_after_model import on_model_error_callback
# from ..callbacks.before_after_tool import on_tool_error_callback
from ..tools.vertex_tools import (
    list_documents_in_store,
    list_available_stores,
    search_file_store,
)


def create_vertex_search_agent(
    name="vertex_search_agent", output_key="vertex_search"
) -> Agent:
    vertex_search_agent = Agent(
        name=name,
        model=config.VERTEX_SEARCH_AGENT_MODEL,
        description="A Vertex AI vector search agent with access to document datastores, containing necessary information. Use it when the user asks to search for information from internal documents and notebooks.",
        instruction="""
        Answer user questions and fetch relevant data based on user's input using tools provided to find information from internal documents and notebooks.
        Be prepared to cite sources or grounding data when asked.
        If you are unsure, which store to use - fetch all available store names and confirm with the customer which one to use.
        """,
        tools=[search_file_store, list_available_stores, list_documents_in_store],
        before_agent_callback=professional_agents_checker,
        # on_model_error_callback=on_model_error_callback,
        # on_tool_error_callback=on_tool_error_callback,
        output_key=output_key,
        planner=config.VERTEX_SEARCH_AGENT_PLANNER,
    )
    return vertex_search_agent
