import os
import requests
import base64
from typing import Dict, List, Union, Optional
from google.adk.tools import FunctionTool

from dotenv import load_dotenv
load_dotenv()
REPO_URL = os.environ.get("GITHUB_DEFAULT_REPO_URL","")
REPO_BRANCH = os.environ.get("GITHUB_DEFAULT_REPO_BRANCH","")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN","")


class GitHubRepoManager:
    """
    Minimal helper for listing / reading / creating / updating files in a GitHub repo.
    Uses Git Data API to perform multi-file commits (blobs -> tree -> commit -> update ref).

    Args:
        token: Personal Access Token (PAT)
        repo: "owner/repo" string
        api_url: GitHub API base (defaults to api.github.com)
    """

    def __init__(self, token: str = GITHUB_TOKEN, repo: str = REPO_URL, api_url: str = "https://api.github.com"):
        if "/" not in repo:
            raise ValueError("repo must be 'owner/repo'")
        self.owner, self.repo = repo.split("/", 1)
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })

    # ---------- low-level helpers ----------
    def _url(self, path: str) -> str:
        return f"{self.api_url}{path}"

    def _get(self, path: str, **kwargs):
        r = self.session.get(self._url(path), **kwargs)
        return r

    def _req_json(self, method: str, path: str, **kwargs):
        r = self.session.request(method, self._url(path), **kwargs)
        if not r.ok:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text}")
        # some endpoints may return 204 No Content with empty body
        return r.json() if r.content else {}

    # ---------- repo metadata ----------
    def get_default_branch(self) -> str:
        repo_info = self._req_json("GET", f"/repos/{self.owner}/{self.repo}")
        return repo_info["default_branch"]

    def branch_exists(self, branch: str) -> bool:
        r = self._get(f"/repos/{self.owner}/{self.repo}/git/ref/heads/{branch}")
        if r.status_code == 200:
            return True
        if r.status_code == 404:
            return False
        r.raise_for_status()
        return False

    # ---------- branch operations ----------
    def create_branch(self, new_branch: str, from_branch: Optional[str] = None) -> dict:
        """Create a new branch pointing at from_branch (default: repo default branch)."""
        if from_branch is None:
            from_branch = self.get_default_branch()
        # get SHA of from_branch
        ref = self._req_json("GET", f"/repos/{self.owner}/{self.repo}/git/ref/heads/{from_branch}")
        base_sha = ref["object"]["sha"]
        return self._req_json("POST", f"/repos/{self.owner}/{self.repo}/git/refs",
                              json={"ref": f"refs/heads/{new_branch}", "sha": base_sha})

    # ---------- listing ----------
    def list_files(self, branch: str, path_prefix: Optional[str] = None) -> List[str]:
        """
        List all file paths in branch (optionally filtered by path_prefix).
        Uses the trees API (recursive).
        """
        # get commit sha for branch
        ref = self._req_json("GET", f"/repos/{self.owner}/{self.repo}/git/ref/heads/{branch}")
        commit_sha = ref["object"]["sha"]
        commit = self._req_json("GET", f"/repos/{self.owner}/{self.repo}/git/commits/{commit_sha}")
        tree_sha = commit["tree"]["sha"]
        tree = self._req_json("GET", f"/repos/{self.owner}/{self.repo}/git/trees/{tree_sha}?recursive=1")
        files = [item["path"] for item in tree.get("tree", []) if item["type"] == "blob"]
        if path_prefix:
            pr = path_prefix.rstrip("/")
            files = [f for f in files if f == pr or f.startswith(pr + "/")]
        return files

    # ---------- read file ----------
    def get_file(self, filepath: str, branch: str) -> Dict:
        """
        Read a file from repo. Returns dict with keys: path, sha, content_bytes, encoding.
        content_bytes is raw bytes (decoded from base64 if necessary).
        """
        r = self._req_json("GET", f"/repos/{self.owner}/{self.repo}/contents/{filepath}", params={"ref": branch})
        content = r.get("content")
        encoding = r.get("encoding", "base64")
        if content is None:
            raw = b""
        else:
            if encoding == "base64":
                raw = base64.b64decode(content)
            else:
                raw = content.encode("utf-8")
        return {"path": r["path"], "sha": r["sha"], "content_bytes": raw, "encoding": encoding}

    # ---------- single-file fallback (contents API) ----------
    def create_or_update_file(self, filepath: str, content: Union[str, bytes], branch: str,
                              commit_message: str = "Update file") -> dict:
        """
        Convenience wrapper for single-file create/update using the Contents API.
        If file exists, provide its sha automatically to update it.
        """
        # check if file exists
        r = self._get(f"/repos/{self.owner}/{self.repo}/contents/{filepath}", params={"ref": branch})
        existing_sha = None
        if r.status_code == 200:
            existing = r.json()
            existing_sha = existing.get("sha")

        if isinstance(content, bytes):
            # contents API expects base64 string when sending encoding=base64
            payload_content = base64.b64encode(content).decode("ascii")
            encoding = "base64"
        else:
            payload_content = content
            encoding = "utf-8"

        body = {"message": commit_message, "content": payload_content, "branch": branch}
        if existing_sha:
            body["sha"] = existing_sha

        return self._req_json("PUT", f"/repos/{self.owner}/{self.repo}/contents/{filepath}", json=body)

    # ---------- multi-file commit (recommended for agent edits) ----------
    def upsert_files(self,
                     files: Union[Dict[str, Union[str, bytes]], List[Dict[str, Union[str, bytes]]]],
                     branch: str,
                     commit_message: str = "Batch update files",
                     create_branch_if_missing: bool = False) -> dict:
        """
        Create or update multiple files in a single commit.

        `files` can be either:
          - mapping: { "path/to/file.py": "file contents", ... }
          - list of dicts: [ {"path": "...", "content": "..."} , ... ]

        If create_branch_if_missing=True and branch doesn't exist, it will be created
        from the repo default branch.
        """
        # normalize input
        if isinstance(files, dict):
            file_items = [{"path": p, "content": c} for p, c in files.items()]
        else:
            file_items = files

        # ensure branch exists (or create it)
        ref_resp = self._get(f"/repos/{self.owner}/{self.repo}/git/ref/heads/{branch}")
        if ref_resp.status_code == 404:
            if create_branch_if_missing:
                self.create_branch(branch)
                ref_resp = self._get(f"/repos/{self.owner}/{self.repo}/git/ref/heads/{branch}")
            else:
                raise RuntimeError(f"Branch '{branch}' does not exist")
        elif not ref_resp.ok:
            ref_resp.raise_for_status()

        head_sha = ref_resp.json()["object"]["sha"]

        # fetch current commit -> base_tree
        commit = self._req_json("GET", f"/repos/{self.owner}/{self.repo}/git/commits/{head_sha}")
        base_tree = commit["tree"]["sha"]

        # create blobs for each file
        tree_entries = []
        for item in file_items:
            path = item["path"]
            content = item["content"]
            if isinstance(content, bytes):
                # binary -> post blob with base64
                blob = self._req_json("POST", f"/repos/{self.owner}/{self.repo}/git/blobs",
                                       json={"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})
            else:
                blob = self._req_json("POST", f"/repos/{self.owner}/{self.repo}/git/blobs",
                                       json={"content": content, "encoding": "utf-8"})
            tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

        # create new tree
        new_tree = self._req_json("POST", f"/repos/{self.owner}/{self.repo}/git/trees",
                                  json={"base_tree": base_tree, "tree": tree_entries})

        # create commit
        new_commit = self._req_json("POST", f"/repos/{self.owner}/{self.repo}/git/commits",
                                    json={"message": commit_message, "tree": new_tree["sha"], "parents": [head_sha]})

        # update branch ref
        updated_ref = self._req_json("PATCH", f"/repos/{self.owner}/{self.repo}/git/refs/heads/{branch}",
                                     json={"sha": new_commit["sha"]})

        return {"commit": new_commit, "tree": new_tree, "ref": updated_ref}

    # ---------- convenience: create PR ----------
    def create_pull_request(self, head_branch: str, base_branch: Optional[str] = None,
                            title: Optional[str] = None, body: str = "") -> dict:
        if base_branch is None:
            base_branch = self.get_default_branch()
        if title is None:
            title = f"Automated changes: {head_branch} -> {base_branch}"
        pr = self._req_json("POST", f"/repos/{self.owner}/{self.repo}/pulls",
                            json={"title": title, "head": head_branch, "base": base_branch, "body": body})
        return pr


repo_manager = GitHubRepoManager()

def list_repo_files(branch: str, prefix: str | None = None) -> dict:
    """
    Lists all file paths in a given branch of the repository.

    Args:
        branch (str): The name of the branch to list files from.
        prefix (str, optional): A path prefix to filter the results. Defaults to None.

    Returns:
        dict: A dictionary containing a list of file paths.
    """
    files = repo_manager.list_files(branch, prefix)
    return {"files": files}

def get_repo_file(filepath: str, branch: str) -> dict:
    """
    Reads a file from the repository and returns its content.

    Args:
        filepath (str): The full path to the file in the repository.
        branch (str): The name of the branch where the file is located.

    Returns:
        dict: A dictionary with file metadata and content.
    """
    return repo_manager.get_file(filepath, branch)

def create_or_update_repo_file(filepath: str, content: Union[str, bytes], branch: str, commit_message: str = "Update file") -> dict:
    """
    Creates a new file or updates an existing one in the repository.

    Args:
        filepath (str): The full path to the file in the repository.
        content (Union[str, bytes]): The content to write to the file.
        branch (str): The name of the branch to commit the change to.
        commit_message (str, optional): The commit message. Defaults to "Update file".

    Returns:
        dict: The API response from GitHub.
    """
    return repo_manager.create_or_update_file(filepath, content, branch, commit_message)

def upsert_repo_files(files: Union[Dict[str, Union[str, bytes]], List[Dict[str, Union[str, bytes]]]], branch: str, commit_message: str = "Batch update files", create_branch_if_missing: bool = False) -> dict:
    """
    Creates or updates multiple files in the repository in a single commit.

    Args:
        files (Union[Dict[str, Union[str, bytes]], List[Dict[str, Union[str, bytes]]]]): 
            A dictionary mapping file paths to content, or a list of dictionaries 
            with 'path' and 'content' keys.
        branch (str): The name of the branch to commit the changes to.
        commit_message (str, optional): The commit message for the batch update. Defaults to "Batch update files".
        create_branch_if_missing (bool, optional): If True, creates the branch if it doesn't exist. Defaults to False.

    Returns:
        dict: The API response from GitHub for the commit.
    """
    return repo_manager.upsert_files(files, branch, commit_message, create_branch_if_missing)

def create_repo_branch(new_branch: str, from_branch: Optional[str] = None) -> dict:
    """
    Creates a new branch in the repository.

    Args:
        new_branch (str): The name of the new branch.
        from_branch (Optional[str], optional): The branch to base the new one on. 
                                            Defaults to the repository's default branch.

    Returns:
        dict: The API response from GitHub.
    """
    return repo_manager.create_branch(new_branch, from_branch)

def create_repo_pull_request(head_branch: str, base_branch: Optional[str] = None, title: Optional[str] = None, body: str = "") -> dict:
    """
    Creates a new pull request.

    Args:
        head_branch (str): The name of the branch with the changes.
        base_branch (Optional[str], optional): The branch to merge the changes into. 
                                             Defaults to the repository's default branch.
        title (Optional[str], optional): The title of the pull request. Defaults to a generated title.
        body (str, optional): The content of the pull request. Defaults to "".

    Returns:
        dict: The API response from GitHub.
    """
    return repo_manager.create_pull_request(head_branch, base_branch, title, body)

list_files_tool = FunctionTool(func=list_repo_files)
get_file_tool = FunctionTool(func=get_repo_file)
create_or_update_file_tool = FunctionTool(func=create_or_update_repo_file)
upsert_files_tool = FunctionTool(func=upsert_repo_files)
create_branch_tool = FunctionTool(func=create_repo_branch)
create_pull_request_tool = FunctionTool(func=create_repo_pull_request)
