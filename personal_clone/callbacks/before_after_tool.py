from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Any

# import re

# from ..tools import search_tools
# from .. import config


# def before_professional_memory_callback(
#     tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
# ) -> Optional[Dict]:
#     """Checks if the user is authorized to see data in a professional tables"""

#     restricted_tables = "memories_professional"
#     user = tool_context.state.get("user_id")
#     tool_name = tool.name
#     if tool_name != "execute_sql":
#         return
#     query = args.get("query", "")
#     if restricted_tables not in query.lower() or user in config.SUPERUSERS:
#         return
#     is_read_only = search_tools.is_read_only(query).get("result")
#     if "memory_id" not in query and not is_read_only:
#         return {"status": "error", "message": "missing required parameter `memory_id`"}

#     elif is_read_only and isinstance(user, str) and user.endswith(config.TEAM_DOMAIN):
#         return

#     pattern = re.compile(
#         r"memory_id\s*=\s*'([^']*)'|memory_id\s+in\s*\(([^)]+)\)", re.IGNORECASE
#     )

#     found_memory_ids = []
#     for single_id, in_clause_content in pattern.findall(query):
#         if single_id:
#             found_memory_ids.append(single_id)
#         elif in_clause_content:
#             ids_from_in = [
#                 part.strip().strip("'\"") for part in in_clause_content.split(",")
#             ]
#             found_memory_ids.extend(ids_from_in)

#     user_ids = search_tools.search_user_id(found_memory_ids)

#     user_valid = any([user == x for x in user_ids.values()])
#     if not user_valid:
#         missing_permissions = {
#             memory: creator for memory, creator in user_ids.items() if creator != user
#         }
#         return {
#             "error": f"You ({user}) cannot modify the following memories `{str(missing_permissions)}`. They were created by other users."
#         }


# def before_rag_edit_callback(
#     tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
# ) -> Optional[Dict]:
#     """Checks if the user is authorized to modify data in RAG storage"""

#     user = tool_context.state.get("user_id")
#     tool_name = tool.name
#     if (
#         tool_name
#         in (
#             "create_corpus",
#             "upload_files_to_corpus",
#             "delete_files_from_corpus",
#             "delete_corpus",
#         )
#         and user not in config.SUPERUSERS
#     ):

#         return {
#             "error": f"You ({user}) cannot modify the existing rag corpora. Please ask Sergey."
#         }


async def on_tool_error_callback(
    tool: BaseTool,
    tool_args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict | None:
    if error:
        return {"status": "error", "message": str(error)}
