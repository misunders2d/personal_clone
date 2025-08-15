import os
import requests
import json

from google.adk.agents import Agent
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

# --- Constants ---

FILTERED_SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api.github.com.fixed.json") # Cached spec file

# --------------------------------------------------
# --- OpenAPI Spec Loading (with Caching)        ---
# --------------------------------------------------

def get_filtered_spec():
    """Loads the filtered spec from cache, or fetches and creates it if it doesn't exist."""
    if os.path.exists(FILTERED_SPEC_PATH):
        print(f"Loading filtered spec from local cache: {FILTERED_SPEC_PATH}")
        with open(FILTERED_SPEC_PATH, 'r') as f:
            return json.load(f)

    print(f"Local spec cache not found at '{FILTERED_SPEC_PATH}'. Fetching and filtering from source...")
    # 1. Define the exact operationIds we want to keep.
    github_operation_filters = {
        "repos/get",
        "repos/get-content",
        "repos/list-for-authenticated-user",
        "repos/create-for-authenticated-user",
        "pulls/list",
        "issues/create",
        "git/get-tree"
    }

    # 2. Fetch the full OpenAPI spec from GitHub.
    GITHUB_SPEC_URL = (
        "https://raw.githubusercontent.com/github/rest-api-description/main/"
        "descriptions/api.github.com/api.github.com.json"
    )
    print("Fetching latest GitHub API spec...")
    github_spec_response = requests.get(GITHUB_SPEC_URL)
    github_spec_response.raise_for_status()
    full_spec_dict = github_spec_response.json()
    print(f"Full spec loaded. Found {len(full_spec_dict.get('paths', {}))} paths.")

    # 3. Filter the spec to only include the desired operations.
    filtered_paths = {}
    for path, path_item in full_spec_dict.get('paths', {}).items():
        filtered_methods = {}
        for method, operation in path_item.items():
            if isinstance(operation, dict) and operation.get('operationId') in github_operation_filters:
                filtered_methods[method] = operation
        if filtered_methods:
            filtered_paths[path] = filtered_methods

    # 4. Create a new, lightweight spec dictionary with the filtered paths.
    filtered_spec_dict = {
        "openapi": full_spec_dict.get("openapi"),
        "info": full_spec_dict.get("info"),
        "servers": full_spec_dict.get("servers"),
        "paths": filtered_paths,
        "components": full_spec_dict.get("components"),
    }
    print(f"Spec filtered. Kept {len(filtered_paths)} paths.")

    # 5. Save the filtered spec to the cache file.
    print(f"Saving filtered spec to local cache: {FILTERED_SPEC_PATH}")
    with open(FILTERED_SPEC_PATH, 'w') as f:
        json.dump(filtered_spec_dict, f, indent=2)
    
    return filtered_spec_dict

# --------------------------------------------------
# --- Toolset and Agent Definition               ---
# --------------------------------------------------

def create_github_toolset():
    # Load the spec using the caching function
    filtered_spec_dict = get_filtered_spec()

    # Create the toolset from the filtered spec dictionary.
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Warning: GITHUB_TOKEN environment variable not set. Some API calls may fail.")

    auth_scheme, auth_credential = token_to_scheme_credential(
        token_type="oauth2Token",
        location="header",
        name="Authorization",
        credential_value=github_token # Let the ADK handle the "Bearer" prefix
    )

    github_toolset = OpenAPIToolset(
        spec_dict=filtered_spec_dict, # Use the filtered dictionary
        auth_scheme=auth_scheme,
        auth_credential=auth_credential,
    )
    return github_toolset

# Define the agent with the filtered toolset.
def create_github_agent():
    root_agent = Agent(
        name="github_agent",
        model=os.environ['MODEL_NAME'],
        tools=[create_github_toolset],
        instruction="""You are a helpful GitHub assistant.
        You have a set of tools to interact with the GitHub API based on user requests.
        Your available tools allow you to:
        - Get repository info and content.
        - Create or update files.
        - List repositories and pull requests.
        - Create issues, pull requests, and new branches.
        Use the tools provided to fulfill the user's request.
        """,
        description="Interacts with the GitHub API using a filtered set of tools from an OpenAPI spec.",
    )
    return root_agent




