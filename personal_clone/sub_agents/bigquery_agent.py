from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.planners import BuiltInPlanner, PlanReActPlanner
from google.genai import types

from typing import Optional, Dict, Any

import re

from ..data import (
    get_current_datetime,
    get_table_data,
    create_bq_agent_instruction,
    table_data,
)
from ..sub_agents.google_search_agent import create_google_search_agent
from ..tools.bigquery_tools import mel_bigquery_toolset
from .. import config

PLANNER = (
    BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)
    )
    if isinstance(config.GOOGLE_FLASH_MODEL, str)
    else PlanReActPlanner()
)


def before_bq_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    """Checks if the user is authorized to see data in a specific table"""

    superusers = [
        "igor@mellanni.com",
        "margarita@mellanni.com",
        "masao@mellanni.com",
        "neel@mellanni.com",
    ]
    user = tool_context.state.get("user_id")
    # user = tool_context._invocation_context.user_id
    tool_name = tool.name

    tables_to_check = []

    query = args.get("query", "")
    if query:
        # Regex to find table names after FROM or JOIN. Handles backticks.
        found_tables = re.findall(
            r"(?:FROM|JOIN)\s+`?([\w.-]+)`?", query, re.IGNORECASE
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

    if tool_name in ("get_table_info", "execute_sql") and len(tables_to_check) == 0:
        return {
            "error": "Access to tables could not be identified and required immediate attention"
        }

    for table_info in tables_to_check:
        project_id = table_info["project_id"]
        dataset_id = table_info["dataset_id"]
        table_id = table_info["table_id"]

        if dataset_id in table_data and table_id in table_data[dataset_id]["tables"]:
            allowed_users = table_data[dataset_id]["tables"][table_id].get(
                "authorized_users"
            )
            if allowed_users and user not in allowed_users + superusers:
                return {
                    "error": f"User {user} does not have access to table `{project_id}.{dataset_id}.{table_id}`. Message `sergey@mellanni.com` if you need access."
                }
    return None


# Agent Definition
def create_bigquery_agent():
    bigquery_agent = Agent(
        model=config.FLASH_MODEL,
        name="bigquery_agent",
        description=(
            "Agent to answer questions about the company's business performance (sales, inventory, payments etc)."
            "Uses BigQuery data and models and executes SQL queries and creates plots."
        ),
        instruction=create_bq_agent_instruction(),
        tools=[
            mel_bigquery_toolset,
            AgentTool(
                agent=create_google_search_agent(name="google_search_for_bq_agent")
            ),
            get_current_datetime,
            get_table_data,
        ],
        planner=PLANNER,
        before_tool_callback=before_bq_callback,
    )
    return bigquery_agent
