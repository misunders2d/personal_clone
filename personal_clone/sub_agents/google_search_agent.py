from google.adk import Agent
from google.adk.tools.google_search_tool import google_search



def create_google_search_agent():
    google_search_agent = Agent(
        name="google_search_agent",
        description="An agent that performs Google searches to find relevant information on the web.",
        model="gemini-2.0-flash-lite",
        instruction="""
        You are an agent that can perform Google searches to find relevant information on the web.
        Use the `google_search_tool` to execute searches based on user queries or specific topics.
        Always provide concise and relevant search results.
        Always include links to the sources of the information you provide.
        """,
        tools=[google_search],
        output_key="google_search_results",
    )
    return google_search_agent


