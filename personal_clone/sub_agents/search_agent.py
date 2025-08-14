from google.adk.agents import Agent
from google.adk.tools import AgentTool, google_search

import os


def create_search_agent_tool(name="web_search_agent"):
    search_agent_tool = AgentTool(
        agent=Agent(
            name=name,
            description="A web search agent that can search the web and find information.",
            instruction="You are a web search agent. Use the `google_search` tool to find relevant information online.",
            tools=[google_search],
            model=os.environ['SEARCH_MODEL_NAME'],
        ),
        skip_summarization=True,
    )
    return search_agent_tool