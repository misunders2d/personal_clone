from datetime import datetime

from google.adk.tools.tool_context import ToolContext


def get_current_datetime(tool_context: ToolContext | None = None):
    """
    Only use this tool if you can't find the datetime information in the {current_datetime} session key.
    """
    current_datetime = datetime.now().isoformat()
    if tool_context:
        cached_datetime = tool_context.state.get("current_datetime", {}).get(
            "datetime", ""
        )

        current_dt_object = datetime.strptime(current_datetime, "%Y-%m-%dT%H:%M:%S.%f")
        cached_dt_object = datetime.strptime(cached_datetime, "%Y-%m-%dT%H:%M:%S.%f")

        if abs(current_dt_object - cached_dt_object).seconds < 60:
            return {
                "status": "error",
                "message": "use {current_datetime} session state key!",
            }
    return {"status": "success", "datetime": datetime.now().isoformat()}
