from google.adk import Agent
from google.adk.tools import google_search

from ..callbacks.before_after_model import google_search_grounding
from .. import config


def create_google_search_agent(name="google_search_agent"):
    google_search_agent = Agent(
        name=name,
        description="An agent that performs Google searches to find relevant information on the web. Grounding data is stored in {google_search_grounding} state key.",
        model=config.GOOGLE_FLASH_MODEL,
        instruction="""
        You are an agent that can perform Google searches to find relevant information on the web.
        Use the `google_search_tool` to execute searches based on user queries or specific topics.
        Always cite sources.
        """,
        tools=[google_search],
        output_key="google_search_results",
        after_model_callback=[google_search_grounding],
    )
    return google_search_agent
