
import os
import subprocess
from typing import List
from dotenv import load_dotenv

load_dotenv()

def list_files(directory: str) -> List[str]:
    """Lists all files in a given directory."""
    try:
        return os.listdir(directory)
    except Exception as e:
        return [f"Error: {e}"]

def read_file(file_path: str) -> str:
    """Reads the content of a file."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

def write_file(file_path: str, content: str) -> str:
    """Writes content to a file."""
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error: {e}"

def run_shell_command(command: str) -> str:
    """Runs a shell command and returns its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {e}"

def get_default_repo_config():
    """Gets the default repository URL and branch from environment variables."""
    repo_url = os.getenv("GITHUB_DEFAULT_REPO_URL")
    repo_branch = os.getenv("GITHUB_DEFAULT_REPO_BRANCH")
    return repo_url, repo_branch
