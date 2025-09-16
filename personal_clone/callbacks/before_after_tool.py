from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool

from typing import Dict, Any, Optional


forbidden_statements = [
"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE", "GRANT", "REVOKE", "RENAME", "COMMIT", "ROLLBACK"]

def memory_agent_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """Inspects/modifies the tool result after execution."""
    # agent_name = tool_context.agent_name
    # tool_name = tool.name


    if (
        tool_response
        and "status" in tool_response
        and not tool_response["status"] == "SUCCESS"
    ):
        # print(f"[TOOL CALLBACK] for {tool_name}: {tool_response['status']}")
        return {
            "actions_needed": f"You MUST search the memory using `memory_agent` for this error: {tool_response}",
            "status": tool_response["status"],
        }

    return None

def before_recall_modifier(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Inspects/modifies tool args or skips the tool call."""
    agent_name = tool_context.agent_name
    tool_name = tool.name
    if tool_name == 'execute_sql' and 'query' in args:
        if any([x.lower() in args.get('query','').lower() for x in forbidden_statements]):
            return {"status":"PASS", "agent_name":agent_name}
