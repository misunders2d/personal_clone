import os
import requests
import base64
from dotenv import load_dotenv

def get_default_repo_config():
    """Gets the default repository URL and branch from environment variables."""
    load_dotenv()
    repo_url = os.getenv("GITHUB_DEFAULT_REPO_URL")
    repo_branch = os.getenv("GITHUB_DEFAULT_REPO_BRANCH")
    return repo_url, repo_branch

def _get_repo_owner_and_name(repo_url: str):
    """Extracts the repository owner and name from the repository URL."""
    owner, name = repo_url.split('github.com/')[-1].split('/')
    if name.endswith('.git'):
        name = name[:-4]
    return owner, name

def get_file_content(repo_url: str, branch: str, file_path: str) -> str:
    """Gets the content of a file from a GitHub repository."""
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    owner, name = _get_repo_owner_and_name(repo_url)
    api_url = f"https://api.github.com/repos/{owner}/{name}/contents/{file_path}?ref={branch}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return content
    elif response.status_code == 404:
        return f"Error: File not found at {file_path}"
    else:
        return f"Error: {response.status_code} - {response.json()['message']}"

def create_or_update_file_content(repo_url: str, branch: str, file_path: str, new_content: str, commit_message: str) -> str:
    """Creates a new file or updates an existing file in a GitHub repository."""
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    owner, name = _get_repo_owner_and_name(repo_url)
    api_url = f"https://api.github.com/repos/{owner}/{name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if the file exists
    response = requests.get(api_url + f"?ref={branch}", headers=headers)
    
    payload = {
        "message": commit_message,
        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
        "branch": branch,
    }

    if response.status_code == 200:
        # File exists, so update it
        payload["sha"] = response.json()["sha"]
        response = requests.put(api_url, headers=headers, json=payload)
    elif response.status_code == 404:
        # File does not exist, so create it
        response = requests.put(api_url, headers=headers, json=payload)
    else:
        return f"Error checking for file: {response.status_code} - {response.json().get('message', '')}"

    if response.status_code in [200, 201]:
        return f"Successfully created/updated {file_path} in {branch} branch."
    else:
        return f"Error creating/updating file: {response.status_code} - {response.json().get('message', '')}"
