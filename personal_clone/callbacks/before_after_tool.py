from google.adk.tools import ToolContext, BaseTool
from typing import Optional, Dict, Any
import re

from ..tools import search_tools
from .. import config


def before_personal_memory_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Checks if the user is authorized to see data in a personal tables"""

    restricted_tables = "personal-clone-464511.memories.memories_personal"
    # user = tool_context._invocation_context.user_id
    user = tool_context.state.get("user_id")
    # tool_name = tool.name

    tables_to_check = []  #

    query = args.get("query", "")
    if query:
        # Regex to find table names after FROM or JOIN. Handles backticks.
        found_tables = re.findall(
            r"(?:FROM|JOIN|UPDATE|INTO)\s+`?([\w.-]+)`?", query, re.IGNORECASE
        )
        for table_name in found_tables:
            parts = table_name.split(".")
            if len(parts) == 3:
                tables_to_check.append(
                    {
                        "project_id": parts[0],
                        "dataset_id": parts[1],
                        "table_id": parts[2],
                    }
                )
            elif len(parts) == 2:
                project_id = args.get("project_id")
                if project_id:
                    tables_to_check.append(
                        {
                            "project_id": project_id,
                            "dataset_id": parts[0],
                            "table_id": parts[1],
                        }
                    )
    else:
        project_id = args.get("project_id")
        dataset_id = args.get("dataset_id")
        table_id = args.get("table_id")
        if all([project_id, dataset_id, table_id]):
            tables_to_check.append(
                {
                    "project_id": project_id,
                    "dataset_id": dataset_id,
                    "table_id": table_id,
                }
            )

    for table_info in tables_to_check:
        project_id = table_info["project_id"]
        dataset_id = table_info["dataset_id"]
        table_id = table_info["table_id"]

        if table_id in restricted_tables and user not in config.SUPERUSERS:
            return {
                "error": f"User {user} does not have access to table `{project_id}.{dataset_id}.{table_id}`. Message Sergey if you need access."
            }
    return None


def before_professional_memory_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Checks if the user is authorized to see data in a professional tables"""

    restricted_tables = "memories_professional"
    user = tool_context.state.get("user_id")
    tool_name = tool.name
    if tool_name != "execute_sql":
        return
    query = args.get("query", "")
    if restricted_tables not in query.lower():
        return
    is_read_only = search_tools.is_read_only(query).get("result")
    if "memory_id" not in query and not is_read_only:
        return {"status": "error", "message": "missing required parameter `memory_id`"}

    elif is_read_only:
        return
    
    pattern = re.compile(
        r"memory_id\s*=\s*'([^']*)'|memory_id\s+in\s*\(([^)]+)\)", re.IGNORECASE
    )

    found_memory_ids = []
    for single_id, in_clause_content in pattern.findall(query):
        if single_id:
            found_memory_ids.append(single_id)
        elif in_clause_content:
            ids_from_in = [
                part.strip().strip("'\"") for part in in_clause_content.split(",")
            ]
            found_memory_ids.extend(ids_from_in)

    user_ids = search_tools.search_user_id(found_memory_ids)

    user_valid = all([user == x for x in user_ids.values()])
    if not user_valid:
        missing_permissions = {
            memory: creator for memory, creator in user_ids.items() if creator != user
        }
        return {
            "error": f"You ({user}) cannot modify the following memories `{str(missing_permissions)}`. They were created by other users."
        }


def before_rag_edit_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Checks if the user is authorized to modify data in RAG storage"""

    user = tool_context.state.get("user_id")
    tool_name = tool.name
    if (
        tool_name
        in (
            "create_corpus",
            "upload_files_to_corpus",
            "delete_files_from_corpus",
            "delete_corpus",
        )
        and user not in config.SUPERUSERS
    ):

        return {
            "error": f"You ({user}) cannot modify the existing rag corpora. Please ask Sergey."
        }
