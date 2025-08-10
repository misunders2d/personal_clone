import os
import base64
from github import Github
from github.GithubException import GithubException

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get('GITHUB_DEFAULT_REPO','')
BRANCH_NAME = os.environ.get('GITHUB_DEFAULT_REPO_BRANCH','development')

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

def get_file_content(file_path: str):
    """
    Gets the content of a file from the GitHub repository.

    Args:
        file_path (str): The path to the file in the repository.

    Returns:
        str: The content of the file, or None if an error occurs.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot get file content.")
        return None
    try:
        contents = repo.get_contents(file_path, ref=BRANCH_NAME) # Specify the branch
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

def _update_file_in_repo(file_path: str, new_content: str, commit_message: str):
    """
    Updates a file in the GitHub repository.

    Args:
        file_path (str): The path to the file in the repository.
        new_content (str): The new content for the file.
        commit_message (str): The commit message for the changes.

    Returns:
        bool: True if the file was updated successfully, False otherwise.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot update file.")
        return False
    try:
        # Get the existing file to get its SHA
        contents = repo.get_contents(file_path, ref=BRANCH_NAME)
        
        # Update the file
        update_data = repo.update_file(
            contents.path,
            commit_message,
            new_content,
            contents.sha,
            branch=BRANCH_NAME # Specify the branch
        )
        print(f"File '{file_path}' updated successfully.")
        return True
    except GithubException as e:
        # Catch specific GitHub API errors
        print(f"GitHub API error updating file '{file_path}': {e}")
        return False
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while updating file '{file_path}': {e}")
        return False

def _create_file_in_repo(file_path: str, content: str, commit_message: str):
    """
    Creates a new file in the GitHub repository.

    Args:
        file_path (str): The path for the new file in the repository.
        content (str): The content of the new file.
        commit_message (str): The commit message for the creation.

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
            branch=BRANCH_NAME # Specify the branch
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

def create_or_update_file(file_path: str, content: str, commit_message: str):
    """
    Creates a new file or updates an existing file in the GitHub repository.

    Args:
        file_path (str): The path to the file in the repository.
        content (str): The content of the file.
        commit_message (str): The commit message for the changes.

    Returns:
        bool: True if the file was created or updated successfully, False otherwise.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot create or update file.")
        return False
    
    try:
        # Check if the file exists
        contents = repo.get_contents(file_path, ref=BRANCH_NAME)
        # If it exists, update it
        return _update_file_in_repo(file_path, content, commit_message)
    except GithubException as e:
        if e.status == 404:
            # If it does not exist, create it
            return _create_file_in_repo(file_path, content, commit_message)
        else:
            # Catch other GitHub API errors
            print(f"GitHub API error checking file '{file_path}': {e.status}")
            print(f"GitHub API error data: {e.data}")
            return False

def list_repo_files():
    """
    Lists all files in the repository recursively.

    Returns:
        list: A list of file paths, or an empty list if an error occurs.
    """
    if repo is None:
        print("Error: GitHub repository not initialized. Cannot list files.")
        return []
    
    files = []
    try:
        contents = repo.get_contents("", ref=BRANCH_NAME)
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path, ref=BRANCH_NAME))
            else:
                files.append(file_content.path)
    except Exception as e:
        print(f"An unexpected error occurred while listing files: {e}")
        return []
    return files

# Example of how to use the functions (optional)
if __name__ == "__main__":
    # Make sure to set the GITHUB_TOKEN environment variable
    if GITHUB_TOKEN is None:
        print("Error: GITHUB_TOKEN environment variable not set.")
    else:
        # Example usage:
        # Get content of a file
        # print("\nAttempting to get README.md content:")
        # file_content = get_file_content("README.md")
        # if file_content:
        #     print("README.md content snippet:")
        #     print(file_content[:200] + "...") # Print first 200 chars
        # else:
        #     print("Failed to retrieve README.md content.")

        # Create a new file (example)
        # print("\nAttempting to create a test file:")
        # new_file_path = "test_file_from_clone.txt"
        # new_file_content = "This is a test file created by the clone script with improved error handling."
        # commit_msg_create = "CI: Create test_file_from_clone.txt"
        # create_success = create_file_in_repo(new_file_path, new_file_content, commit_msg_create)
        # if not create_success:
        #     print("Failed to create test file.")

        # Update a file (example - uncomment and modify path/content to test)
        # print("\nAttempting to update a file:")
        # existing_file_path = "README.md" # Example: update README.md
        # original_content = get_file_content(existing_file_path)
        # if original_content:
        #     updated_content = original_content + "\n\n# This is an appended line for testing updates."
        #     commit_msg_update = "CI: Update README.md with appended line"
        #     update_success = update_file_in_repo(existing_file_path, updated_content, commit_msg_update)
        #     if not update_success:
        #         print(f"Failed to update {existing_file_path}.")
        # else:
        #      print(f"Could not retrieve content for {existing_file_path} to test update.")
        
        # List all files in the repo
        # print("\nAttempting to list all files in the repo:")
        # all_files = list_repo_files()
        # if all_files:
        #     print("All files in the repo:")
        #     for file_path in all_files:
        #         print(file_path)
        # else:
        #     print("Failed to list files in the repo.")
        pass

