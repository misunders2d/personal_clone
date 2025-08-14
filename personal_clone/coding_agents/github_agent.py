import asyncio
import os
import uuid

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

# --- Constants ---
APP_NAME_GITHUB = "github_api_app"
USER_ID_GITHUB = "user_github_1"
SESSION_ID_GITHUB = f"session_github_{uuid.uuid4()}"
AGENT_NAME_GITHUB = "github_interaction_agent"
GEMINI_MODEL = "gemini-2.5-flash"

# --- Load OpenAPI Specification ---
spec_path = os.path.join(os.path.dirname(__file__), "api.github.com.fixed.json")
with open(spec_path, "r") as f:
    openapi_spec_string = f.read()

# --- Create OpenAPIToolset ---
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    print("Warning: GITHUB_TOKEN environment variable not set. Some API calls may fail.")

auth_scheme, auth_credential = token_to_scheme_credential(
    token_type="oauth2Token",
    location="header",
    name="Authorization",
    credential_value=github_token
)

github_toolset = OpenAPIToolset(
    spec_str=openapi_spec_string,
    spec_str_type='json',
    auth_scheme=auth_scheme,
    auth_credential=auth_credential,
)

# --- Agent Definition ---
def create_github_agent():
    root_agent = Agent(
        name=AGENT_NAME_GITHUB,
        model=GEMINI_MODEL,
        tools=[github_toolset],
        instruction="""You are a GitHub assistant.
        Use the available tools to interact with the GitHub API.
        Fulfill user requests by calling the appropriate functions.
        """,
        description="Interacts with the GitHub API using tools generated from an OpenAPI spec."
    )
    return root_agent

# --- Session and Runner Setup ---
async def setup_session_and_runner():
    session_service_github = InMemorySessionService()
    runner_github = Runner(
        agent=create_github_agent(),
        app_name=APP_NAME_GITHUB,
        session_service=session_service_github,
    )
    await session_service_github.create_session(
        app_name=APP_NAME_GITHUB,
        user_id=USER_ID_GITHUB,
        session_id=SESSION_ID_GITHUB,
    )
    return runner_github

# --- Agent Interaction Function ---
async def call_github_agent_async(query, runner_github):
    print(f"--- Running GitHub Agent ---")
    print(f"Query: {query}")

    content = types.Content(role='user', parts=[types.Part(text=query)])
    final_response_text = "Agent did not provide a final text response."
    try:
        async for event in runner_github.run_async(
            user_id=USER_ID_GITHUB, session_id=SESSION_ID_GITHUB, new_message=content
            ):
            if event.get_function_calls():
                call = event.get_function_calls()[0]
                print(f"  Agent Action: Called function '{call.name}' with args {call.args}")
            elif event.get_function_responses():
                response = event.get_function_responses()[0]
                print(f"  Agent Action: Received response for '{response.name}'")
            elif event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[0].text.strip()

        print(f"Agent Final Response: {final_response_text}")

    except Exception as e:
        print(f"An error occurred during agent run: {e}")
        import traceback
        traceback.print_exc()
    print("-" * 30)

# --- Run Examples ---
async def run_github_example():
    runner_github = await setup_session_and_runner()

    # Example: Get user information
    await call_github_agent_async("can you list me files in misunders2d/personal_clone?'", runner_github)
    
    # Example: List repositories for a user
    # await call_github_agent_async("List the repositories for the user 'microsoft'", runner_github)


# --- Execute ---
if __name__ == "__main__":
    print("Executing GitHub API example...")
    try:
        asyncio.run(run_github_example())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            print("Info: Cannot run asyncio.run from a running event loop (e.g., Jupyter/Colab).")
        else:
            raise e
    print("GitHub API example finished.")