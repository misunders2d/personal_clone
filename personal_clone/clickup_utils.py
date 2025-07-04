import os
import requests
from typing import Optional
from datetime import datetime, timezone

class ClickUpAPI:
    def __init__(self):
        self.api_token = os.getenv("CLICKUP_API_TOKEN")
        self.space_id = os.getenv("CLICKUP_SPACE_ID")
        self.list_id = os.getenv("CLICKUP_LIST_ID")
        self.user_email = os.getenv("CLICKUP_USER_EMAIL")
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.clickup.com/api/v2"

    def get_authorized_teams(self):
        """Fetches the authorized teams (workspaces) for the authenticated user."""
        url = f"{self.base_url}/team"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return {"teams": response.json().get('teams', [])}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching authorized teams: {e}"}

    def get_spaces(self, team_id: str):
        """Fetches spaces within a given team (workspace)."""
        url = f"{self.base_url}/team/{team_id}/space"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return {"spaces": response.json().get('spaces', [])}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching spaces: {e}"}

    def get_lists(self, folder_id: str):
        """Fetches lists within a given folder or space."""
        url = f"{self.base_url}/folder/{folder_id}/list"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return {"lists": response.json().get('lists', [])}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching lists: {e}"}

    def _get_user_id(self, email: str):
        """Fetches the user ID for a given email across all authorized teams."""
        teams_response = self.get_authorized_teams()
        if "error" in teams_response:
            return {"error": teams_response["error"]}

        for team in teams_response.get("teams", []):
            for member in team.get("members", []):
                if member.get("user", {}).get("email") == email:
                    return {"user_id": member["user"]["id"]}
        return {"error": f"User with email {email} not found in any authorized team."}

    def _format_timestamp(self, timestamp: Optional[str]) -> Optional[str]:
        """Converts a Unix timestamp (in milliseconds) to a human-readable date string."""
        if timestamp:
            try:
                # ClickUp timestamps are in milliseconds
                dt_object = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
                return dt_object.strftime('%Y-%m-%d %H:%M:%S UTC')
            except ValueError:
                return None
        return None

    def get_tasks(self):
        if not self.list_id:
            return {"error": "ClickUp List ID not provided in .env."}

        url = f"{self.base_url}/list/{self.list_id}/task"
        params = {}
        
        if self.user_email:
            user_id_response = self._get_user_id(self.user_email)
            if "error" in user_id_response:
                return {"error": user_id_response["error"]}
            user_id = user_id_response["user_id"]
            params["assignees[]"] = [user_id] # ClickUp API uses assignees[] for filtering by assignee ID

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            tasks_data = response.json().get('tasks', [])
            
            formatted_tasks = []
            for task in tasks_data:
                formatted_task = {
                    "id": task.get("id"),
                    "name": task.get("name"),
                    "description": task.get("description"),
                    "status": task.get("status", {}).get("status"),
                    "due_date": self._format_timestamp(task.get("due_date"))
                }
                formatted_tasks.append(formatted_task)
            return {"tasks": formatted_tasks}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching tasks: {e}"}

    def create_task(self, title: str, description: Optional[str] = None, due_date: Optional[int] = None, start_date: Optional[int] = None):
        if not self.list_id:
            return {"error": "ClickUp List ID not provided in .env."}

        url = f"{self.base_url}/list/{self.list_id}/task"
        payload = {
            "name": title,
            "description": description or "",
        }

        if self.user_email:
            user_id_response = self._get_user_id(self.user_email)
            if "error" in user_id_response:
                return {"error": user_id_response["error"]}
            user_id = user_id_response["user_id"]
            payload["assignees"] = [user_id]

        if due_date:
            payload["due_date"] = due_date
        if start_date:
            payload["start_date"] = start_date

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return {"task": response.json()}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error creating task: {e}"}

    def close_task(self, task_id: str):
        if not task_id:
            return {"error": "Task ID not provided."}

        url = f"{self.base_url}/task/{task_id}"
        payload = {
            "status": "complete" # Assuming "complete" is a valid status to close a task
        }
        try:
            response = requests.put(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return {"task": response.json()}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error closing task: {e}"}

# Example Usage (for testing purposes, not part of the module itself)
if __name__ == "__main__":
    # Set dummy environment variables for testing
    os.environ["CLICKUP_API_TOKEN"] = "pk_YOUR_CLICKUP_API_TOKEN"
    os.environ["CLICKUP_SPACE_ID"] = "YOUR_SPACE_ID"
    os.environ["CLICKUP_LIST_ID"] = "YOUR_LIST_ID"
    os.environ["CLICKUP_USER_EMAIL"] = "test@example.com"

    clickup_api = ClickUpAPI()

    # To test, you'll need a valid API token and user email.
    # You can then use get_authorized_teams(), get_spaces(team_id), and get_lists(folder_id)
    # to find the IDs you need for create_task, get_tasks, and close_task.

    # Example: Get authorized teams
    # teams = clickup_api.get_authorized_teams()
    # print("Authorized Teams:", teams)

    # Example: Get spaces in a team (replace YOUR_TEAM_ID)
    spaces = clickup_api.get_spaces("YOUR_TEAM_ID")
    print("Spaces:", spaces)

    # Example: Get lists in a folder/space (replace YOUR_FOLDER_OR_SPACE_ID)
    # lists = clickup_api.get_lists("YOUR_FOLDER_OR_SPACE_ID")
    # print("Lists:", lists)

    # Example: Create a task (replace YOUR_LIST_ID and YOUR_USER_EMAIL if not set in .env)
    # new_task = clickup_api.create_task("Test Task from Agent", "This is a test description.", list_id="YOUR_LIST_ID", email="test@example.com")
    # print("Created Task:", new_task)

    # Example: Get tasks (replace YOUR_LIST_ID and YOUR_USER_EMAIL if not set in .env)
    # tasks = clickup_api.get_tasks(list_id="YOUR_LIST_ID", email="test@example.com")
    # print("All Tasks:", tasks)

    # Example: Close a task (replace YOUR_TASK_ID)
    # closed_task = clickup_api.close_task("YOUR_TASK_ID")
    # print("Closed Task:", closed_task)
