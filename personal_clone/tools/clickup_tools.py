import requests
from google.adk.tools import ToolContext

# from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
# from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
# from mcp import StdioServerParameters


from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from .. import config

API_BASE_URL = "https://api.clickup.com/api/v2"

HEADERS = {"Authorization": config.CLICKUP_API_TOKEN}


def create_timestamp_ms_from_local(
    year: int, month: int, day: int, hour: int, minute: int, utc_offset_hours: int
) -> int:
    """
    Creates a Unix timestamp in milliseconds for a given local date, time, and UTC offset.
    This function does not automatically handle daylight saving time changes.
    The 'utc_offset_hours' must be provided and should reflect the correct offset
    (including any daylight saving adjustments if applicable) for the given datetime.

    Args:
        year (int): The year (e.g., 2025).
        month (int): The month (1-12).
        day (int): The day of the month (1-31).
        hour (int): The hour (0-23).
        minute (int): The minute (0-59).
        utc_offset_hours (int): The fixed offset from UTC in hours.
                                (e.g., +3 for UTC+3, -5 for UTC-5).

    Returns:
        int: The Unix timestamp in milliseconds.
    """

    local_dt = datetime(year, month, day, hour, minute)
    offset_td = timedelta(hours=utc_offset_hours)
    tz_offset = timezone(offset_td)
    aware_local_dt = local_dt.replace(tzinfo=tz_offset)
    utc_dt = aware_local_dt.astimezone(timezone.utc)
    return int(utc_dt.timestamp() * 1000)


def get_clickup_user(tool_context: ToolContext):
    """
    Retrieve a ClickUp user object information.
    Use this tool as a starting point to get the user's teams and spaces.

    Returns:
        Dict: A dictionary with user information and their teams and spaces.
        The dictionary contains:
            - 'user_email': The email of the user.
            - 'user_teams': Information about the user and their teams.
            - 'user_spaces': A list of spaces the user has access to, each with its statuses.

    """
    url = f"{API_BASE_URL}/team"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    email = tool_context.state.get("user_id", "")

    user_info = {"user_email": email, "user_teams": [], "user_spaces": []}

    try:
        teams = resp.json().get("teams", [])
        for team in teams:
            team_info = {"id": team["id"], "name": team["name"]}
            member_info = [
                {
                    "id": x["user"]["id"],
                    "username": x["user"]["username"],
                    "email": x["user"]["email"],
                }
                for x in team.get("members", [])
            ]
            team_info["members"] = member_info
            user_info["user_teams"].append(team_info)
            space_url = f"{API_BASE_URL}/team/{team['id']}/space"
            space_response = requests.get(space_url, headers=HEADERS)
            space_response.raise_for_status()
            spaces = space_response.json().get("spaces", [])
            spaces_dict = [
                {"id": x["id"], "name": x["name"], "statuses": x["statuses"]}
                for x in spaces
            ]
            user_info["user_spaces"].append(spaces_dict)
        tool_context.state["clickup_user_info"] = user_info
        return user_info

    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_clickup_user_by_email(email: str):
    """
    Retrieve a ClickUp user object.

    """
    url = f"{API_BASE_URL}/team"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    try:
        teams = resp.json().get("teams", [])
        for team in teams:
            for member in team.get("members", []):
                if member.get("user", {}).get("email") == email:
                    return member.get("user")
    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_folders_and_lists(space_id: str):
    """
    List folders and lists for a given space.

    Args:
        space_id (str): The ID of the space. Use `get_clickup_user` to get the full user info and find space ID.

    Returns:
        Dict[List[Dict[str, Any]]]: A list of folder objects and lists objects under the space.
    """
    result = {}
    folder_url = f"{API_BASE_URL}/space/{space_id}/folder"
    list_url = f"{API_BASE_URL}/space/{space_id}/list"
    try:
        resp = requests.get(folder_url, headers=HEADERS)
        resp.raise_for_status()
        result["folders"] = resp.json().get("folders", [])
        resp = requests.get(list_url, headers=HEADERS)
        resp.raise_for_status()
        result["lists"] = resp.json().get("lists", [])
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_tasks_for_user(
    tool_context: ToolContext,
    team_id: str,
    list_id: Optional[str] = None,
    folder_id: Optional[str] = None,
    status: Optional[str] = None,
    due: Optional[str] = None,
):
    """
    List tasks assigned to a specific user, with filters for list, status, and due date.

    Args:
        team_id (str): The ClickUp team ID. Use `get_clickup_user` to get the full user info including team ID.
        list_id (Optional[str]): Restrict results to a specific list ID. If None, searches across the entire team.
        folder_id (Optional[str]): Restrict results to a specific folder ID. If None, searches across the entire team.
        status (Optional[str]): Task status filter:
            - "open" or "done" → maps to ClickUp's `include_closed` param.
        due (Optional[str]): Due date filter:
            - "today" → tasks due before midnight today.
            - "tomorrow" → tasks due tomorrow.
            - "week"/"next week" → tasks due in the next 7 days.
            - "overdue" → tasks with due date earlier than now.

    Returns:
        List[Dict[str, Any]]: List of task objects.

    Raises:
        ValueError: If the user or team cannot be found in ClickUp.
        requests.HTTPError: If the ClickUp API returns an error response.
    """
    email = tool_context.state.get("user_id", "")
    if not email:
        return {
            "status": "failed",
            "error": "ToolContext.state['user_id'] is missing (expected user email).",
        }

    user_info = get_clickup_user(tool_context)
    if not user_info or "user_teams" not in user_info:
        return {
            "status": "failed",
            "error": "Could not retrieve user/team info from ClickUp.",
        }

    # Locate the team
    target_team = next((t for t in user_info["user_teams"] if t["id"] == team_id), None)  # type: ignore
    if not target_team:
        return {
            "status": "failed",
            "error": f"Team with ID {team_id} not found for this user.",
        }

    # Locate the user in that team
    member = next((m for m in target_team["members"] if m["email"] == email), None)  # type: ignore
    if not member:
        return {
            "status": "failed",
            "error": f"User {email} is not a member of team {team_id}.",
        }

    user_id = member["id"]  # type: ignore

    params = {
        "assignees[]": user_id,
        "archived": "false",
        "subtasks": "true",
    }

    # --- Status filter ---
    if status:
        status_lower = status.lower()
        if status_lower == "open":
            params["include_closed"] = "false"
        elif status_lower == "closed":
            params["include_closed"] = "true"
        else:
            params["statuses[]"] = status  # use exact ClickUp status name

    # --- Due date filter ---
    now = datetime.now(timezone.utc)
    start_ts, end_ts = None, None

    if due:
        due = due.lower()
        if due == "today":
            start_ts = int(
                datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp()
                * 1000
            )
            end_ts = int(
                (
                    datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                    + timedelta(days=1)
                ).timestamp()
                * 1000
            )
        elif due == "tomorrow":
            start_ts = int(
                (
                    datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                    + timedelta(days=1)
                ).timestamp()
                * 1000
            )
            end_ts = int(
                (
                    datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                    + timedelta(days=2)
                ).timestamp()
                * 1000
            )
        elif due in ["week", "next week"]:
            start_ts = int(now.timestamp() * 1000)
            end_ts = int((now + timedelta(days=7)).timestamp() * 1000)
        elif due == "overdue":
            end_ts = int(now.timestamp() * 1000)

    if start_ts:
        params["due_date_gt"] = start_ts
    if end_ts:
        params["due_date_lt"] = end_ts

    # --- Endpoint selection ---
    if list_id:
        url = f"{API_BASE_URL}/list/{list_id}/task"
    elif folder_id:
        url = f"{API_BASE_URL}/folder/{folder_id}/task"
    else:
        url = f"{API_BASE_URL}/team/{team_id}/task"

    all_tasks = []
    page = 0
    while True:
        params["page"] = page
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        tasks_page = data.get("tasks", [])
        all_tasks.extend(tasks_page)

        if data.get("last_page", False) or not tasks_page:
            break
        page += 1

    clean_tasks = [
        {
            "id": x.get("id"),
            "name": x.get("name"),
            "text_content": x.get("text_content"),
            "description": x.get("description"),
            "status": x.get("status", {}).get("status", ""),
            "status_type": x.get("status", {}).get("type", ""),
            "date_created": x.get("date_created"),
            "creator": x.get("creator"),
            "assignees": x.get("assignees", []),
            "due_date": x.get("due_date"),
            "url": x.get("url"),
        }
        for x in all_tasks
    ]
    if status and status.lower() == "open":
        return [
            task
            for task in clean_tasks
            if task.get("status_type", "") in ("open", "custom")
        ]
    elif status and status.lower() == "closed":
        return [task for task in clean_tasks if task.get("status_type", "") == "done"]
    else:
        return clean_tasks


def get_task(task_id: str) -> dict:
    """
    Get details for a specific task by its ID.

    Args:
        task_id (str): The ID of the task (e.g., 'abc-123').

    Returns:
        dict: The full task object from the ClickUp API.
    """
    url = f"{API_BASE_URL}/task/{task_id}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def create_task(
    list_id: str,
    name: str,
    description: str,
    due_date: Optional[int],
    assignees: Optional[List[str]] = None,
    due_date_time: Optional[bool] = None,
    parent_task_id: Optional[str] = None,
):
    """
    Create a task in a given list. If `parent_task_id` is provided, creates a subtask of a given parent task.

    Args:
        list_id (str): The ID of the list where the task should be created.
        name (str): The name/title of the task.
        description (str): The task description.
        due_date (Optional[int]): Epoch ms (UTC). If None, no due date is set.
        assignees (Optional[List[str]]): A list of user emails to assign the task to.
        due_date_time (Optional[bool]): If True, ClickUp will treat the due_date as including a time.
            If False, it's an all-day date. If None, function auto-detects based on the epoch-ms:
            non-zero time component -> True, otherwise False.
        parent_task_id (Optional[str]): If provided, creates the task as a subtask of the given parent task ID.
    Returns:
        Dict[str, Any]: The created task info as returned by ClickUp.
    """
    try:
        assignee_ids = []
        if assignees:
            for email in assignees:
                user = get_clickup_user_by_email(email)
                if user:
                    assignee_ids.append(user["id"])

        payload: Dict[str, Any] = {
            "name": name,
            "description": description,
        }
        if assignee_ids:
            payload["assignees"] = assignee_ids

        if due_date is not None:
            payload["due_date"] = due_date
            if due_date_time is None:
                has_time = (due_date % 86_400_000) != 0
                payload["due_date_time"] = bool(has_time)
            else:
                payload["due_date_time"] = bool(due_date_time)
        if parent_task_id:
            payload["parent"] = parent_task_id

        url = f"{API_BASE_URL}/list/{list_id}/task"
        resp = requests.post(url, headers=HEADERS, json=payload)
        resp.raise_for_status()
        result = resp.json()
        return {"status": "success", "task_url": result["url"], "task_id": result["id"]}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def get_task_link(task_id: str) -> str:
    """
    Get the direct link to a ClickUp task for manual deletion.

    Args:
        task_id (str): The ID of the task.

    Returns:
        str: The web URL of the task in ClickUp.
    """
    return f"https://app.clickup.com/t/{task_id}"


clickup_toolset = [
    create_timestamp_ms_from_local,
    get_clickup_user,
    list_folders_and_lists,
    list_tasks_for_user,
    get_task,
    create_task,
    get_task_link,
]


# def create_clickup_toolset():
#     clickup_toolset = McpToolset(
#         connection_params=StdioConnectionParams(
#             server_params=StdioServerParameters(
#                 command="npx",
#                 args=[
#                     "-y",
#                     "@taazkareem/clickup-mcp-server@latest",
#                 ],
#                 env={
#                     "CLICKUP_API_KEY": config.CLICKUP_API_TOKEN,
#                     "CLICKUP_TEAM_ID": config.CLICKUP_TEAM_ID,
#                     # "DOCUMENT_SUPPORT": "true",
#                 },
#             ),
#         ),
#     )
#     return clickup_toolset


# def create_official_clickup_toolset():
#     clickup_toolset = McpToolset(
#         connection_params=StdioConnectionParams(
#             server_params=StdioServerParameters(
#                 command="npx",
#                 args=[
#                     "-y",
#                     "mcp-remote",
#                     "https://mcp.clickup.com/mcp",
#                 ],
#                 env={
#                     "CLICKUP_API_KEY": config.CLICKUP_API_TOKEN,
#                     "CLICKUP_TEAM_ID": config.CLICKUP_TEAM_ID,
#                     # "DOCUMENT_SUPPORT": "true",
#                 },
#             ),
#         ),
#     )
#     return clickup_toolset
