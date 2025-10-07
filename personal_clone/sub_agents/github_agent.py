from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from ..tools.web_search_tools import scrape_web_page

from .. import config


def create_github_tollset():
    github_toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-github",
                ],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": config.GITHUB_TOKEN},
            ),
        ),
    )
    return github_toolset


def create_github_agent():
    github_agent = Agent(
        model=config.FLASH_MODEL,
        name='github_agent',
        instruction=f"""
        You are a skilled GitHub agent with access to a github toolset.
        The default repo where YOUR code lives is {config.DEFAULT_GITHUB_REPO}.
        Your task is to self-evolve and fix your own code, add functionality and always improve.
        IMPORTANT! Your code uses Google ADK (Agent Development Kit) platform - before you plan any changes you MUST look up your own codebase to understand how it works.
        The user may ask you to add features or functions - collaborate as much as you can.
        Assume that your knowledge is outdated and you must refresh it from the up-to-date sources.
        You should always use your `scrape_web_page` tool to get more understanding of a certain feature.
        Do not EVER push commits or create PRs to the master branch - always create a feature branch first.
        Always ask for user confirmation if your actions are about to make changes to the codebase.
        """,
        tools=[create_github_tollset(), scrape_web_page],
    )
    return github_agent