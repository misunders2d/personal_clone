from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool

from typing import Dict, Any, Optional


def memory_agent_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """Inspects/modifies the tool result after execution."""
    agent_name = tool_context.agent_name
    tool_name = tool.name
    # print("$" * 80)
    # print(type(tool_response))
    # print(tool_response)
    # print("$" * 80)

    if "status" in tool_response and not tool_response["status"] == "SUCCESS":
        # print(f"[TOOL CALLBACK] for {tool_name}: {tool_response['status']}")
        return {
            "actions_needed": f"You MUST search the memory using `memory_agent` for this error: {tool_response}",
            "status": tool_response["status"],
        }

    return None
