from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from .. import config


def create_pinecone_toolset():
    pinecone_toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@pinecone-database/mcp",
                ],
                env={"PINECONE_API_KEY": config.PINECONE_API_KEY},
            ),
        ),
    )
    return pinecone_toolset
