import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_file_content(repo_url: str, branch: str, file_path: str) -> str:
    """Gets the content of a file from a GitHub repository."""
    api_url = f"https://api.github.com/repos/{repo_url.split('github.com/')[-1]}/contents/{file_path}?ref={branch}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return content
    else:
        return f"Error: {response.status_code} - {response.json()['message']}"

def update_file_content(repo_url: str, branch: str, file_path: str, new_content: str, commit_message: str) -> str:
    """Updates the content of a file in a GitHub repository."""
    repo_owner, repo_name = repo_url.split('github.com/')[-1].split('/')
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 1. Get the SHA of the file
    get_file_url = f"{api_url}/contents/{file_path}?ref={branch}"
    response = requests.get(get_file_url, headers=headers)
    if response.status_code != 200:
        return f"Error getting file SHA: {response.status_code} - {response.json().get('message', '')}"
    file_sha = response.json()['sha']

    # 2. Create a new blob with the updated content
    create_blob_url = f"{api_url}/git/blobs"
    new_content_encoded = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
    create_blob_payload = {
        "content": new_content_encoded,
        "encoding": "base64",
    }
    response = requests.post(create_blob_url, headers=headers, json=create_blob_payload)
    if response.status_code != 201:
        return f"Error creating blob: {response.status_code} - {response.json().get('message', '')}"
    new_blob_sha = response.json()['sha']

    # 3. Get the SHA of the latest commit on the branch
    get_branch_url = f"{api_url}/branches/{branch}"
    response = requests.get(get_branch_url, headers=headers)
    if response.status_code != 200:
        return f"Error getting branch info: {response.status_code} - {response.json().get('message', '')}"
    latest_commit_sha = response.json()['commit']['sha']

    # 4. Get the SHA of the base tree of the latest commit
    get_commit_url = f"{api_url}/git/commits/{latest_commit_sha}"
    response = requests.get(get_commit_url, headers=headers)
    if response.status_code != 200:
        return f"Error getting commit info: {response.status_code} - {response.json().get('message', '')}"
    base_tree_sha = response.json()['tree']['sha']

    # 5. Create a new tree with the new blob
    create_tree_url = f"{api_url}/git/trees"
    create_tree_payload = {
        "base_tree": base_tree_sha,
        "tree": [
            {
                "path": file_path,
                "mode": "100644",
                "type": "blob",
                "sha": new_blob_sha,
            }
        ],
    }
    response = requests.post(create_tree_url, headers=headers, json=create_tree_payload)
    if response.status_code != 201:
        return f"Error creating tree: {response.status_code} - {response.json().get('message', '')}"
    new_tree_sha = response.json()['sha']

    # 6. Create a new commit
    create_commit_url = f"{api_url}/git/commits"
    create_commit_payload = {
        "message": commit_message,
        "tree": new_tree_sha,
        "parents": [latest_commit_sha],
    }
    response = requests.post(create_commit_url, headers=headers, json=create_commit_payload)
    if response.status_code != 201:
        return f"Error creating commit: {response.status_code} - {response.json().get('message', '')}"
    new_commit_sha = response.json()['sha']

    # 7. Update the branch reference to point to the new commit
    update_ref_url = f"{api_url}/git/refs/heads/{branch}"
    update_ref_payload = {
        "sha": new_commit_sha,
    }
    response = requests.patch(update_ref_url, headers=headers, json=update_ref_payload)
    if response.status_code == 200:
        return f"Successfully updated {file_path} in {branch} branch."
    else:
        return f"Error updating branch reference: {response.status_code} - {response.json().get('message', '')}"
