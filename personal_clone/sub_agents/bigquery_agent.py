from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.planners import BuiltInPlanner
from google.genai import types

from typing import Optional, Dict, Any

import re

from data import (
    BIGQUERY_AGENT_MODEL,
    get_current_datetime,
    create_bq_agent_instruction,
    table_data,
)
from .gogle_search_agent import google_search_agent_tool
from ..tools.bigquery_tools import (
    credentials,
    create_plot,
    load_artifact_to_temp_bq,
    save_tool_output_to_artifact,
)

tool_config = BigQueryToolConfig(
    write_mode=WriteMode.BLOCKED, max_query_result_rows=10000
)


credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# Instantiate a BigQuery toolset
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
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
    user = tool_context._invocation_context.user_id
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


def after_table_save_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """Checks if the table view was presented to prevent the agent from duplicating the output"""

    tool_name = tool.name

    if (
        tool_name == "save_tool_output_to_artifact"
        and tool_response["status"] == "SUCCESS"
    ):
        return {
            "WARNING": "The table data has been presented to the user in downloadable format, DON'T SHOW THIS DATA TO THE USER!!!"
        }

    return None


# Agent Definition
def create_bigquery_agent():
    bigquery_agent = Agent(
        model=BIGQUERY_AGENT_MODEL,
        name="bigquery_agent",
        description=(
            "Agent to answer questions about the company's business performance (sales, inventory, payments etc)."
            "Uses BigQuery data and models and executes SQL queries and creates plots."
        ),
        instruction=create_bq_agent_instruction(),
        tools=[
            bigquery_toolset,
            google_search_agent_tool(name="bigquery_search_agent"),
            get_current_datetime,
            create_plot,
            load_artifact_to_temp_bq,
            save_tool_output_to_artifact,
        ],
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        ),
        before_tool_callback=before_bq_callback,
        after_tool_callback=after_table_save_callback,
    )
    return bigquery_agent
