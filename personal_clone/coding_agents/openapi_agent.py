
"""This file defines the OpenAPI agent for dynamic tool acquisition."""

import os

from google.adk.agents import Agent

from ..sub_agents.search_agent import create_search_agent_tool
from ..utils.openapi_utils import (
    create_persistent_openapi_tool,
    fetch_spec_from_url,
    run_temporary_openapi_tool,
)


def create_openapi_agent(name="openapi_agent") -> Agent:
    """Creates an agent specialized in handling OpenAPI specifications and wraps it as a tool."""

    openapi_agent = Agent(
        name=name,
        description="An agent that can find, process, and integrate tools from OpenAPI specifications.",
        instruction="""You are an OpenAPI specialist agent. Your goal is to handle a user's request to integrate a new tool or service.

Follow these steps:
1.  You will be given a high-level goal, like "Integrate the Stripe API to manage customers."
2.  From this goal, identify the service name (e.g., "Stripe").
3.  Use your `web_search_agent` tool to find the URL for the service's official OpenAPI v3 specification.
4.  Use the `fetch_spec_from_url` tool with the URL you found to get the raw content of the specification.
5.  After you successfully retrieve the spec, you **MUST** ask the user the following question:
    *"I have found the specification for [Service Name]. Should I create a (P)ersistent new tool for it, or use it for a (T)emporary run to answer your query?"*
6.  Based on the user's response ('P' or 'T'), call either the `create_persistent_openapi_tool` or `run_temporary_openapi_tool` tool to execute their choice. For persistent tools, you will need to get the current branch name from the user or context to pass to the tool.
""",
        model=os.environ.get("MODEL_NAME", "gemini-1.5-flash-latest"),
        tools=[
            create_search_agent_tool("web_search_agent"),
            fetch_spec_from_url,
            create_persistent_openapi_tool,
            run_temporary_openapi_tool,
        ],
    )

    return openapi_agent
