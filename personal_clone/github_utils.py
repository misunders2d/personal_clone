import os
import base64
import streamlit as st
from typing import Optional
from github import Github
from github.GithubException import GithubException

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", st.secrets["GITHUB_TOKEN"])
REPO_NAME = os.environ.get('GITHUB_DEFAULT_REPO', st.secrets["GITHUB_DEFAULT_REPO"])
BRANCH_NAME = os.environ.get('GITHUB_DEFAULT_REPO_BRANCH', st.secrets["GITHUB_DEFAULT_REPO_BRANCH"])

# Initialize GitHub API
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    print("GitHub repository initialized successfully.")
except GithubException as e:
    print(f"Error initializing GitHub API or getting repository: {e}")
    # Handle the error appropriately, e.g., exit or set a flag
    repo = None # Indicate that the repository is not accessible
except Exception as e:
    print(f"An unexpected error occurred during GitHub initialization: {e}")
    repo = None

def get_file_content(file_path: str, branch: Optional[str] = None):
    """
    Gets the content of a file from the GitHub repository.

    Args:
        file_path (str): The path to the file in the repository.
        branch (str, optional): The name of the branch to get the file from. Defaults to the default branch.

    Returns:
        str: The content of the file, or None if an error occurs.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot get file content.")
        return None
    try:
        contents = repo.get_contents(file_path, ref=branch or BRANCH_NAME) # Specify the branch
        if isinstance(contents, list):
            print(f"Error: The path '{file_path}' refers to a directory, not a file.")
            return None
        decoded_content = base64.b64decode(contents.content).decode('utf-8')
        return decoded_content
    except GithubException as e:
        # Catch specific GitHub API errors, e.g., file not found (404)
        print(f"GitHub API error getting file content for '{file_path}': {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while getting file content for '{file_path}': {e}")
        return None

def _create_file_in_repo(file_path: str, content: str, commit_message: str, branch: Optional[str] = None):
    """
    Creates a new file in the GitHub repository.

    Args:
        file_path (str): The path for the new file in the repository.
        content (str): The content of the new file.
        commit_message (str): The commit message for the creation.
        branch (str, optional): The name of the branch to create the file in. Defaults to the default branch.

    Returns:
        bool: True if the file was created successfully, False otherwise.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot create file.")
        return False
    try:
        repo.create_file(
            file_path,
            commit_message,
            content,
            branch=branch or BRANCH_NAME # Specify the branch
        )
        print(f"File '{file_path}' created successfully.")
        return True
    except GithubException as e:
        # Catch specific GitHub API errors, e.g., file already exists (422)
        print(f"GitHub API error creating file '{file_path}': {e}")
        return False
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while creating file '{file_path}': {e}")
        return False

def create_or_update_file(file_path: str, content: str, commit_message: str, branch: Optional[str] = None):
    """
    Creates a new file or updates an existing file in the GitHub repository.
    For updates, it uses the file's SHA for a safe, atomic update.

    Args:
        file_path (str): The path to the file in the repository.
        content (str): The content of the file.
        commit_message (str): The commit message for the changes.
        branch (str, optional): The name of the branch to create or update the file in. Defaults to the default branch.

    Returns:
        bool: True if the file was created or updated successfully, False otherwise.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot create or update file.")
        return False
    
    try:
        # Check if the file exists to get its SHA for updating
        contents = repo.get_contents(file_path, ref=branch or BRANCH_NAME)
        # If get_contents returns a list, the path is a directory, which is not supported for file updates
        if isinstance(contents, list):
            print(f"Error: The path '{file_path}' refers to a directory, not a file.")
            return False

        # If it exists, update it using its SHA
        repo.update_file(
            contents.path,
            commit_message,
            content,
            contents.sha,
            branch=branch or BRANCH_NAME
        )
        print(f"File '{file_path}' updated successfully.")
        return True
    except GithubException as e:
        if e.status == 404:
            # If the file does not exist, create it.
            return _create_file_in_repo(file_path, content, commit_message, branch)
        else:
            # Catch other GitHub API errors during the get_contents or update_file call
            print(f"GitHub API error handling file '{file_path}': {e}")
            return False
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while creating or updating file '{file_path}': {e}")
        return False

def list_repo_files(branch: Optional[str] = None):
    """
    Lists all files in the repository recursively.

    Args:
        branch (str, optional): The name of the branch to list files from. Defaults to the default branch.

    Returns:
        list: A list of file paths, or an empty list if an error occurs.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot list files.")
        return []
    
    all_files = []
    dirs_to_visit = [""]  # Start with the root directory
    try:
        while dirs_to_visit:
            path = dirs_to_visit.pop()
            contents = repo.get_contents(path, ref=branch or BRANCH_NAME)
            if isinstance(contents, list):
                for file_content in contents:
                    if file_content.type == "dir":
                        dirs_to_visit.append(file_content.path)
                    else:
                        all_files.append(file_content.path)
            else:
                # It's a single file, not a directory
                all_files.append(contents.path)
    except Exception as e:
        print(f"An unexpected error occurred while listing files: {e}")
        return []
    return all_files

def create_branch(base_branch: str, new_branch_name: str) -> Optional[str]:
    """
    Creates a new branch from a specified base branch.

    Args:
        base_branch (str): The name of the branch to create the new branch from.
        new_branch_name (str): The name of the new branch to create.

    Returns:
        str: The name of the new branch if successful, None otherwise.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot create branch.")
        return None
    try:
        # Get the base branch reference
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        # Create the new branch
        repo.create_git_ref(f"refs/heads/{new_branch_name}", base_ref.object.sha)
        return(f"Branch '{new_branch_name}' created successfully from '{base_branch}'.")
    except GithubException as e:
        return(f"GitHub API error creating branch '{new_branch_name}': {e}")
    except Exception as e:
        return(f"An unexpected error occurred while creating branch '{new_branch_name}': {e}")

def create_pull_request(title: str, body: str, head_branch: str, base_branch: str) -> Optional[str]:
    """
    Creates a pull request.

    Args:
        title (str): The title of the pull request.
        body (str): The body/description of the pull request.
        head_branch (str): The name of the branch where the changes are (feature branch).
        base_branch (str): The name of the branch to merge the changes into (e.g., 'development').

    Returns:
        str: The URL of the created pull request if successful, None otherwise.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot create pull request.")
        return None
    try:
        pull = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )
        print(f"Pull request '{title}' created successfully: {pull.html_url}")
        return pull.html_url
    except GithubException as e:
        print(f"GitHub API error creating pull request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while creating pull request: {e}")
        return None
