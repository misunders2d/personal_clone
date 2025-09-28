from google.adk.tools import ToolContext, BaseTool
from typing import Optional, Dict, Any
import re

from .. import config


def before_memory_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Checks if the user is authorized to see data in a personal tables"""

    restricted_tables = "personal-clone-464511.memories.memories_personal"
    # user = tool_context._invocation_context.user_id
    user = tool_context.state.get("user_id")
    print(f"[MEMORY TOOL CALLBACK]: USER IDENTIFIED AS {user}", end="\n\n\n")
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
