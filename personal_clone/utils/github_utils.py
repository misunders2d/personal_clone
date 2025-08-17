# github_utils.py
"""
This module provides functions to interact with the GitHub API using PyGithub.
It requires the GITHUB_TOKEN environment variable to be set.
To install the library: pip install PyGithub
"""

import os
import asyncio
from github import Github, GithubException, UnknownObjectException

from google.adk.tools import FunctionTool, BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.agents.readonly_context import ReadonlyContext

from typing import Optional, List


def _get_repo(repo_owner: str, repo_name: str):
    """Helper function to get a repository object."""
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set.")
    g = Github(github_token)
    try:
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        return repo
    except UnknownObjectException:
        raise ValueError(
            f"Repository '{repo_owner}/{repo_name}' not found or token is invalid."
        )


def list_files_in_repo(
    repo_owner: str, repo_name: str, branch: str = "main", path: str = "/"
):
    """
    Lists all files in the repository recursively from a given path.
    Args:
        repo_owner: The owner of the repository.
        repo_name: The name of the repository.
        branch: The branch to list files from. Defaults to 'main'.
        path: The path to start listing from. Defaults to root.
    Returns:
        A list of file paths or an error dictionary.
    """
    try:
        repo = _get_repo(repo_owner, repo_name)
        ref = repo.get_git_ref(f"heads/{branch}")
        tree = repo.get_git_tree(ref.object.sha, recursive=True)
        file_list = [element.path for element in tree.tree if element.type == "blob"]
        if path != "/":
            return [f for f in file_list if f.startswith(path)]
        return file_list
    except (GithubException, UnknownObjectException) as e:
        return {"error": f"Error listing files in branch '{branch}': {e}"}


def get_file_content(
    repo_owner: str, repo_name: str, file_path: str, branch: str = "main"
):
    """
    Gets the content of a file.
    Args:
        repo_owner: The owner of the repository.
        repo_name: The name of the repository.
        file_path: The path to the file.
        branch: The branch where the file is located. Defaults to 'main'.
    Returns:
        The file content as a string or an error dictionary.
    """
    try:
        repo = _get_repo(repo_owner, repo_name)
        content_file = repo.get_contents(file_path, ref=branch)
        if isinstance(content_file, list):
            return {"error": f"'{file_path}' is a directory, not a file."}
        if content_file.type == "file":
            return content_file.decoded_content.decode("utf-8")
        else:
            return {"error": f"'{file_path}' is not a file."}
    except UnknownObjectException:
        return {"error": f"File '{file_path}' not found in branch '{branch}'."}
    except GithubException as e:
        return {"error": f"Error getting file content: {e}"}


def create_or_update_file(
    repo_owner: str,
    repo_name: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str = "main",
):
    """
    Creates a new file or updates an existing one in a specific branch.
    Args:
        repo_owner: The owner of the repository.
        repo_name: The name of the repository.
        file_path: The path to the file.
        content: The new content of the file.
        commit_message: The commit message.
        branch: The branch to commit to. Defaults to 'main'.
    Returns:
        A dictionary with the status and commit SHA, or an error dictionary.
    """
    try:
        repo = _get_repo(repo_owner, repo_name)
        try:
            file_content = repo.get_contents(file_path, ref=branch)
            result = repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=file_content.sha,  # type: ignore
                branch=branch,
            )
            return {"status": "updated", "commit_sha": result["commit"].sha}
        except UnknownObjectException:
            result = repo.create_file(
                path=file_path, message=commit_message, content=content, branch=branch
            )
            return {"status": "created", "commit_sha": result["commit"].sha}
    except GithubException as e:
        return {"error": f"Error creating or updating file: {e}"}


def create_branch(
    repo_owner: str, repo_name: str, new_branch_name: str, source_branch: str = "main"
):
    """
    Creates a new branch from a source branch.
    Args:
        repo_owner: The owner of the repository.
        repo_name: The name of the repository.
        new_branch_name: The name of the new branch.
        source_branch: The source branch. Defaults to 'main'.
    Returns:
        A dictionary with the status, or an error dictionary.
    """
    try:
        repo = _get_repo(repo_owner, repo_name)
        source = repo.get_branch(source_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=source.commit.sha)
        return {"status": "success", "branch": new_branch_name}
    except GithubException as e:
        if e.status == 422 and "Reference already exists" in str(e.data):
            return {"error": f"Branch '{new_branch_name}' already exists."}
        return {"error": f"Error creating branch: {e}"}


def create_pull_request(
    repo_owner: str,
    repo_name: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
):
    """
    Creates a pull request.
    Args:
        repo_owner: The owner of the repository.
        repo_name: The name of the repository.
        title: The title of the pull request.
        body: The body of the pull request.
        head_branch: The branch with the changes.
        base_branch: The branch to merge into. Defaults to 'main'.
    Returns:
        A dictionary with the PR number and URL, or an error dictionary.
    """
    try:
        repo = _get_repo(repo_owner, repo_name)
        pr = repo.create_pull(
            title=title, body=body, head=head_branch, base=base_branch
        )
        return {"status": "success", "pr_number": pr.number, "url": pr.html_url}
    except GithubException as e:
        return {"error": f"Error creating pull request: {e}"}


class GithubToolset(BaseToolset):
    def __init__(self, prefix="github_"):
        self.prefix = prefix
        self._get_repo = FunctionTool(
            func=_get_repo,
        )
        self._list_files_in_repo = FunctionTool(
            func=list_files_in_repo,
        )
        self._get_file_content = FunctionTool(
            func=get_file_content,
        )
        self._create_or_update_file = FunctionTool(
            func=create_or_update_file,
        )
        self._create_branch = FunctionTool(
            func=create_branch,
        )
        self._create_pull_request = FunctionTool(
            func=create_pull_request,
        )
        print(f"GithubToolset initialized with prefix '{self.prefix}'")

    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> List[BaseTool]:
        tools_to_return = [
            self._list_files_in_repo,
            self._get_file_content,
            self._create_or_update_file,
            self._create_branch,
            self._create_pull_request,
        ]
        print(f"GithubToolset providing tools: {[t.name for t in tools_to_return]}")
        return tools_to_return #type: ignore

    async def close(self) -> None:
        # No resources to clean up in this simple example
        print(f"SimpleMathToolset.close() called for prefix '{self.prefix}'.")
        await asyncio.sleep(0)  # Placeholder for async cleanup if needed


def create_github_toolset():
    github_toolset = GithubToolset(prefix="github_")
    return github_toolset
