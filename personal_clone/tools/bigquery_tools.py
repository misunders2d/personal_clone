import pandas as pd
from google.cloud import bigquery
from modules.gcloud_modules import normalize_columns
import io
from datetime import datetime, timedelta
import uuid
from io import StringIO

import tempfile
from .. import config
import os
import json
from google.oauth2 import service_account


import plotly.graph_objects as go
from google.adk.tools.tool_context import ToolContext
from google.genai.types import Part


bigquery_service_account_info = json.loads(config.MELL_GCP_SERVICE_ACCOUNT_INFO)

# set google application credentials to use BigQuery tools
with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_json:
    temp_json.write(config.MELL_GCP_SERVICE_ACCOUNT_INFO)
    temp_json.flush()
    MELL_GCP_SERVICE_ACCOUNT_INFO = json.load(open(temp_json.name))

credentials = service_account.Credentials.from_service_account_info(MELL_GCP_SERVICE_ACCOUNT_INFO)


async def create_plot(
    tool_context: ToolContext,
    data_list: list[dict],
    series_list: list[dict],
    x_axis: str,
    title: str,
    colors_dict: dict,
    y_axis_title: str,
    y2_axis_title: str,
    bar_mode: str = "group",  # "group" | "stack" | "overlay"
) -> dict:
    """
    Generates a flexible plot (pie, bar, line, scatter, area) and saves it as an artifact.

    Args:
        tool_context: ADK tool context.
        data_list: list of values of the dataset (list of dicts).
        series_list: dict list describing each series. Example:
            [
              {"y": "sales", "type": "bar", "name": "Sales", "axis": "primary"},
              {"y": "conversion_rate", "type": "line", "name": "Conversion %", "axis": "secondary"},
              {"type": "pie", "values": "sales", "labels": "region", "name": "Sales by Region"}
            ]
        x_axis: Column name for x-axis (ignored for pie).
        title: Title of the chart.
        colors_dict: a dict mapping series names to colors as a JSON string.
        y_axis_title: Label for the primary y-axis.
        y2_axis_title: Label for the secondary y-axis.
        bar_mode: How to display multiple bars. One of "group", "stack", "overlay".
    Returns:
        dict: a dictionary with the status and message
    """

    user = tool_context._invocation_context.user_id

    try:
        df = pd.DataFrame(data_list)
        series = series_list
        colors = colors_dict

        fig = go.Figure()

        # Add traces
        for s in series:
            s_type = s.get("type", "line")
            name = s.get("name", s.get("y", "Series"))
            axis = s.get("axis", "primary")
            color = colors.get(name)

            if s_type == "line":
                fig.add_trace(
                    go.Scatter(
                        x=df[x_axis],
                        y=df[s["y"]],
                        mode="lines",
                        name=name,
                        yaxis="y2" if axis == "secondary" else "y",
                        line=dict(color=color) if color else None,
                    )
                )

            elif s_type == "scatter":
                fig.add_trace(
                    go.Scatter(
                        x=df[x_axis],
                        y=df[s["y"]],
                        mode="markers",
                        name=name,
                        yaxis="y2" if axis == "secondary" else "y",
                        marker=dict(color=color) if color else None,
                    )
                )

            elif s_type == "bar":
                fig.add_trace(
                    go.Bar(
                        x=df[x_axis],
                        y=df[s["y"]],
                        name=name,
                        yaxis="y2" if axis == "secondary" else "y",
                        marker=dict(color=color) if color else None,
                    )
                )

            elif s_type == "area":
                fig.add_trace(
                    go.Scatter(
                        x=df[x_axis],
                        y=df[s["y"]],
                        name=name,
                        fill="tozeroy",
                        yaxis="y2" if axis == "secondary" else "y",
                        line=dict(color=color) if color else None,
                    )
                )

            elif s_type == "pie":
                fig.add_trace(
                    go.Pie(
                        values=df[s["values"]],
                        labels=df[s["labels"]],
                        name=name,
                        hole=s.get("hole", 0),  # support donut if hole > 0
                        marker=(
                            dict(colors=[colors.get(val) for val in df[s["labels"]]])
                            if colors
                            else None
                        ),
                    )
                )

            else:
                return {
                    "status": "FAILED",
                    "message": f"Error: Unsupported chart type '{s_type}'.",
                }

        # Layout (skip axes if only pie charts)
        has_pie = any(s.get("type") == "pie" for s in series)
        if not has_pie:
            fig.update_layout(
                title=title,
                xaxis=dict(title=x_axis),
                yaxis=dict(title=y_axis_title),
                yaxis2=dict(title=y2_axis_title, overlaying="y", side="right"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                barmode=(
                    bar_mode if bar_mode in ["group", "stack", "overlay"] else "group"
                ),
            )
        else:
            fig.update_layout(title=title)

        # Export to HTML
        html_str = fig.to_html(full_html=False, include_plotlyjs="cdn")
        html_bytes = html_str.encode("utf-8")

        # Save artifact
        plot_artifact = Part.from_bytes(data=html_bytes, mime_type="text/html")
        filename = f"{user}:{title.replace(' ', '_')}.html"
        version = await tool_context.save_artifact(
            filename=filename, artifact=plot_artifact
        )

        return {
            "status": "SUCCESS",
            "message": f"Successfully created and saved interactive plot '{filename}' (version {version}).",
        }

    except Exception as e:
        return {"status": "FAILED", "message": f"Error while creating plot: {e}"}


async def load_artifact_to_temp_bq(tool_context: ToolContext, filename: str) -> dict:
    """
    Upload a CSV/Excel artifact into BigQuery as a temporary table for quick file analysis
    (auto-deletes after 1 hour).
    Args:
        tool_context: ADK tool context.
        filename: file name of the file in the artifact service.

    """
    artifact = await tool_context.load_artifact(filename)
    if not artifact or not artifact.inline_data or not artifact.inline_data.data:
        return {"status": "FAILED", "message": f"Artifact {filename} not found."}

    data = bytes(artifact.inline_data.data)
    mime = artifact.inline_data.mime_type or ""

    if "csv" in mime or filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(data))
    elif "excel" in mime or filename.endswith((".xls", ".xlsx", ".xlsm")):
        df = pd.read_excel(io.BytesIO(data))
    else:
        return {"status": "FAILED", "message": f"Unsupported artifact type: {mime}"}

    df = normalize_columns(df)

    with bigquery.Client(
        credentials=credentials, project=credentials.project_id
    ) as client:
        try:
            # Create unique temp table name
            table_id = f"mellanni-project-da.auxillary_development.tmp_{filename.replace('.', '_')}_{int(datetime.now().timestamp())}"

            job = client.load_table_from_dataframe(df, table_id)
            job.result()  # wait for upload

            # Set expiration time (1 hour from now)
            table = client.get_table(table_id)
            table.expires = datetime.now() + timedelta(hours=1)
            client.update_table(table, ["expires"])
        except Exception as e:
            return {
                "status": "FAILED",
                "message": f"Failed to upload file for analysis, convert it to .csv for better compatibility:\n{e}",
            }

    return {
        "status": "SUCCESS",
        "message": f"Uploaded `{filename}` to temporary BigQuery table `{table_id}` (expires in 1 hour).",
    }


async def save_tool_output_to_artifact(
    tool_context: ToolContext, tool_response: dict
) -> dict:
    """
    Saves the received Bigquery tool response to artifacts. Always use this tool to present table data.

    Args:
        tool_response (dict): the tool response dict, containing "rows" - usually the response from execute_sql tool
    Returns:
        dict: a status and an important message
    """

    user = tool_context._invocation_context.user_id
    try:
        filename = f"{user}:Table_{uuid.uuid4()}.csv"
        df = pd.DataFrame(tool_response["rows"])
        buf = StringIO()
        df.to_csv(buf, index=False)

        df_artifact = Part.from_bytes(
            data=buf.getvalue().encode("utf-8"), mime_type="text/csv"
        )
        await tool_context.save_artifact(filename=filename, artifact=df_artifact)
        return {
            "status": "SUCCESS",
            "message": f"The table has been presented to the user in the artifact service with the filename {filename}. Do not show the table data again to avoid duplication",
        }
    except Exception as e:
        return {"status": "FAILED", "MESSAGE": f"The following error occurred: {e}"}
