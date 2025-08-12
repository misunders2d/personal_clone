from langchain.tools import tool
import os
from github import Github

# Initialize the GitHub API with your token
# You should store your token securely, e.g., in an environment variable
g = Github(os.environ.get("GITHUB_TOKEN"))

@tool
def create_github_issue(title: str, body: str, repo_name: str = "PamarjotS/personal-clone-test"):
    """
    Creates a new GitHub issue in the specified repository.

    Args:
        title (str): The title of the issue.
        body (str): The body (description) of the issue.
        repo_name (str): The name of the repository (e.g., "PamarjotS/personal-clone-test").

    Returns:
        str: The URL of the created issue, or an error message.
    """
    try:
        repo = g.get_user().get_repo(repo_name.split('/')[-1])
        issue = repo.create_issue(title=title, body=body)
        return issue.html_url
    except Exception as e:
        return f"Error creating GitHub issue: {e}"

@tool
def get_github_issue(issue_number: int, repo_name: str = "PamarjotS/personal-clone-test"):
    """
    Retrieves a GitHub issue from the specified repository.

    Args:
        issue_number (int): The number of the issue to retrieve.
        repo_name (str): The name of the repository (e.g., "PamarjotS/personal-clone-test").

    Returns:
        dict: A dictionary containing issue details (title, body, state, URL), or an error message.
    """
    try:
        repo = g.get_user().get_repo(repo_name.split('/')[-1])
        issue = repo.get_issue(issue_number)
        return {
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "url": issue.html_url
        }
    except Exception as e:
        return f"Error retrieving GitHub issue: {e}"

@tool
def get_open_github_issues(repo_name: str = "PamarjotS/personal-clone-test"):
    """
    Retrieves all open GitHub issues from the specified repository.

    Args:
        repo_name (str): The name of the repository (e.g., "PamarjotS/personal-clone-test").

    Returns:
        list: A list of dictionaries, each containing details of an open issue (title, number, URL), or an error message.
    """
    try:
        repo = g.get_user().get_repo(repo_name.split('/')[-1])
        open_issues = repo.get_issues(state='open')
        issues_list = []
        for issue in open_issues:
            issues_list.append({
                "title": issue.title,
                "number": issue.number,
                "url": issue.html_url
            })
        return issues_list
    except Exception as e:
        return f"Error retrieving open GitHub issues: {e}"

@tool
def edit_github_issue(issue_number: int, title: str = None, body: str = None, state: str = None, repo_name: str = "PamarjotS/personal-clone-test"):
    """
    Edits an existing GitHub issue in the specified repository.

    Args:
        issue_number (int): The number of the issue to edit.
        title (str, optional): The new title for the issue.
        body (str, optional): The new body (description) for the issue.
        state (str, optional): The new state for the issue ('open' or 'closed').
        repo_name (str): The name of the repository (e.g., "PamarjotS/personal-clone-test").

    Returns:
        str: The URL of the edited issue, or an error message.
    """
    try:
        repo = g.get_user().get_repo(repo_name.split('/')[-1])
        issue = repo.get_issue(issue_number)
        issue.edit(title=title, body=body, state=state)
        return issue.html_url
    except Exception as e:
        return f"Error editing GitHub issue: {e}"
