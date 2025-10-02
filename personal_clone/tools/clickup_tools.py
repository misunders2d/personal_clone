import requests
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools import FunctionTool, ToolContext
from google.adk.agents.readonly_context import ReadonlyContext

from typing import List, Optional
import asyncio
from datetime import datetime, timedelta, timezone

from .. import config

API_BASE_URL = "https://api.clickup.com/api/v2"

HEADERS = {"Authorization": config.CLICKUP_API_TOKEN}


def get_clickup_user(tool_context: ToolContext):
    """
    Retrieve a ClickUp user object.

    """
    url = f"{API_BASE_URL}/team"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    email = tool_context.state.get("user_id", "")

    try:
        teams = resp.json().get("teams", [])
        for team in teams:
            for member in team.get("members", []):
                if member.get("user", {}).get("email") == email:
                    return member.get("user")
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



def list_teams(tool_context: ToolContext):
    """
    List all teams available for the user.

    """
    user = get_clickup_user(tool_context)
    if not user:
        return []

    url = f"{API_BASE_URL}/team"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("teams", [])


def list_spaces(team_id: str):
    """
    List spaces for a given team.

    Args:
        team_id (str): The ID of the team. Use `list_teams` to get the team ID.

    Returns:
        List[Dict[str, Any]]: A list of space objects under the team.
    """
    url = f"{API_BASE_URL}/team/{team_id}/space"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("spaces", [])


def list_folders(space_id: str):
    """
    List folders for a given space.

    Args:
        space_id (str): The ID of the space. Use `list_spaces` to get the space ID.

    Returns:
        List[Dict[str, Any]]: A list of folder objects under the space.
    """
    url = f"{API_BASE_URL}/space/{space_id}/folder"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("folders", [])


def list_lists(folder_id: str):
    """
    List lists for a given folder.

    Args:
        folder_id (str): The ID of the folder. Use `list_folders` to get the folder ID.

    Returns:
        List[Dict[str, Any]]: A list of list objects under the folder.
    """
    url = f"{API_BASE_URL}/folder/{folder_id}/list"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("lists", [])


def list_tasks_for_user(
    tool_context: ToolContext, team_id: str, status: Optional[str] = None, due: Optional[str] = None
):
    """
    List all tasks assigned to a specific user across a team,
    with optional filters for status and due date.

    Args:
        team_id (str): The ClickUp team ID. Use `list_teams` to get the team ID.
        status (Optional[str]): Task status filter ("open", "closed", or a specific status name).
        due (Optional[str]): Due date filter ("today", "tomorrow", "week", "overdue").

    Returns:
        List[Dict[str, Any]]: A list of task objects matching the filters.
    """
    user = get_clickup_user(tool_context)
    if not user:
        return []

    user_id = user["id"]

    params = {
        "assignees[]": user_id,
        "archived": "false",
        "subtasks": "true",
    }

    # Handle status filter
    if status:
        if status.lower() in ["open", "closed"]:
            params["statuses[]"] = status.lower()
        else:
            params["statuses[]"] = status  # custom ClickUp status name

    # Handle due date filter
    now = datetime.now(timezone.utc)
    start_ts = None
    end_ts = None

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

    # Query API
    url = f"{API_BASE_URL}/team/{team_id}/task"
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json().get("tasks", [])


def create_task(
    list_id: str,
    name: str,
    description: str,
    assignees: Optional[List[str]] = None,
    due_date: Optional[int] = None,
):
    """
    Create a task in a given list.

    Args:
        list_id (str): The ID of the list where the task should be created. Use `list_lists` to get the list ID.
        name (str): The name/title of the task.
        description (str): The task description.
        assignees (Optional[List[str]]): A list of user emails to assign the task to.
        due_date (Optional[int]): The due date timestamp in milliseconds (epoch).

    Returns:
        Dict[str, Any]: The created task object as returned by the ClickUp API.
    """
    assignee_ids = []
    if assignees:
        for email in assignees:
            user = get_clickup_user_by_email(email)
            if user:
                assignee_ids.append(user["id"])

    payload = {
        "name": name,
        "description": description,
        "assignees": assignee_ids,
    }
    if due_date:
        payload["due_date"] = due_date

    url = f"{API_BASE_URL}/list/{list_id}/task"
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()


def get_task_link(task_id: str) -> str:
    """
    Get the direct link to a ClickUp task for manual deletion.

    Args:
        task_id (str): The ID of the task.

    Returns:
        str: The web URL of the task in ClickUp.
    """
    return f"https://app.clickup.com/t/{task_id}"


# class ClickupToolset(BaseToolset):
#     name = ("clickup_tools",)
#     description = ("A set of tools for interacting with the ClickUp API.",)

#     def __init__(self, prefix: str = "clickup_"):
#         self.prefix = prefix
#         self.get_user_by_email = FunctionTool(func=get_user_by_email)
#         self.list_teams = FunctionTool(func=list_teams)
#         self.list_spaces = FunctionTool(func=list_spaces)
#         self.list_folders = FunctionTool(func=list_folders)
#         self.list_lists = FunctionTool(func=list_lists)
#         self.create_task = FunctionTool(func=create_task)
#         self.get_task_link = FunctionTool(func=get_task_link)
#         self.list_tasks_for_user = FunctionTool(func=list_tasks_for_user)

#     async def get_tools( #type: ignore
#         self, readonly_context: Optional[ReadonlyContext] = None
#     ) -> List[FunctionTool]:
#         tools_to_return = [
#             self.get_user_by_email,
#             self.list_teams,
#             self.list_spaces,
#             self.list_folders,
#             self.list_lists,
#             self.create_task,
#             self.get_task_link,
#             self.list_tasks_for_user,
#         ]
#         return tools_to_return

#     async def close(self) -> None:
#         await asyncio.sleep(0)


# def create_clickup_toolset():
#     clickup_toolset = ClickupToolset()
#     return clickup_toolset
