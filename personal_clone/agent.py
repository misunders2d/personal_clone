from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
from typing import Optional, Any
import pytz
from pydantic import PrivateAttr

from datetime import datetime

from .search import (
    write_to_rag,
    read_from_rag,
    update_in_rag,
    delete_from_rag,
    find_experiences,
)
from .clickup_utils import ClickUpAPI
from .github_utils import (
    get_file_content,
    list_repo_files,
    create_or_update_file,
    create_branch,
    create_pull_request,
    BRANCH_NAME # Import the default branch name
)
from .instructions import (
    DEVELOPER_AGENT_INSTRUCTION, 
    MASTER_AGENT_INSTRUCTION,
    CODE_REVIEWER_AGENT_INSTRUCTION,
    PLAN_FETCHER_AGENT_INSTRUCTION,
    PLANNER_AGENT_INSTRUCTION
    )


# --- Constants ---
SEARCH_MODEL_NAME='gemini-2.5-flash'
MODEL_NAME='gemini-2.5-flash'
MASTER_AGENT_MODEL='gemini-2.5-pro'

# --- Ancillary Services & Tools ---
clickup_api = ClickUpAPI()

def get_current_date():
    """
    Returns the current date and time in YYYY-MM-DD HH:MM:SS format
    for Kiev and New York timezones.
    """
    # Define timezones
    kiev_tz = pytz.timezone("Europe/Kiev")
    new_york_tz = pytz.timezone("America/New_York")

    # Get current UTC time
    utc_now = datetime.now(pytz.utc)

    # Convert to Kiev time
    kiev_time = utc_now.astimezone(kiev_tz)

    # Convert to New York time
    new_york_time = utc_now.astimezone(new_york_tz)

    # Format times
    kiev_formatted = kiev_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    new_york_formatted = new_york_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    return {
        "kiev_time": kiev_formatted,
        "new_york_time": new_york_formatted
    }

search_agent_tool = AgentTool(
    agent=Agent(
        name="web_search_agent",
        description="A web search agent that can search the web and find information.",
        instruction="You are a web search agent. Use the `google_search` tool to find relevant information online.",
        tools=[google_search],
        model=SEARCH_MODEL_NAME
    ),
    skip_summarization=True)

# --- Developer Workflow Sub-Agents ---

planner_agent = Agent(
    name="planner_agent",
    description="Creates and refines development plans.",
    instruction=PLANNER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    tools=[
        search_agent_tool,
        list_repo_files,
        get_file_content,
        exit_loop
    ], output_key='development_plan'
)

code_reviewer_agent = Agent(
    name="code_reviewer_agent",
    description="Reviews development plans for quality and adherence to project standards.",
    instruction=CODE_REVIEWER_AGENT_INSTRUCTION,
    model=LiteLlm('openai/gpt-4.1-nano'),
    tools=[
        get_file_content,
        list_repo_files,
        search_agent_tool,
    ],
    output_key='reviewer_feedback'
)

plan_fetcher_agent = Agent(
    name="plan_fetcher_agent",
    description="Refines development plans based on reviewer feedback.",
    instruction=PLAN_FETCHER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    tools=[],
)

# --- Workflow Agents ---

code_review_loop = LoopAgent(
    name="review_loop",
    description="A loop agent that creates and reviews development plans iteratively to achieve best results.",
    sub_agents=[planner_agent, code_reviewer_agent],
    max_iterations=5)


plan_and_review_agent = SequentialAgent(
    name="plan_and_review_agent",
    description="An agent that creates a development plan and reviews it iteratively until approved.",
    sub_agents = [code_review_loop, plan_fetcher_agent],
    )

# --- Primary User-Facing Agents ---

class DeveloperAgent(Agent):
    _feature_branch_name: Optional[str] = PrivateAttr(None)
    _base_branch: str = PrivateAttr(BRANCH_NAME)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set up tools and sub_agents after self is available
        self.tools = [
            self._create_or_update_file_wrapper,
            self._get_file_content_wrapper,
            self._list_repo_files_wrapper,
            search_agent_tool,
            self.setup_feature_branch,
            self.create_pr,
        ]
        self.sub_agents = [plan_and_review_agent] # Add back sub_agent

    def _create_or_update_file_wrapper(self, file_path: str, content: str, commit_message: str):
        """
        Wrapper for create_or_update_file that uses the active feature branch.
        """
        return create_or_update_file(file_path, content, commit_message, branch=self._feature_branch_name or self._base_branch) # type: ignore

    def _get_file_content_wrapper(self, file_path: str):
        """
        Wrapper for get_file_content that uses the active feature branch.
        """
        return get_file_content(file_path, branch=self._feature_branch_name or self._base_branch) # type: ignore

    def _list_repo_files_wrapper(self):
        """
        Wrapper for list_repo_files that uses the active feature branch.
        """
        return list_repo_files(branch=self._feature_branch_name or self._base_branch) # type: ignore

    def setup_feature_branch(self, task_description: str) -> str:
        """
        Creates a new feature branch for the current development task.

        Args:
            task_description (str): A brief description of the task for naming the branch.

        Returns:
            str: The name of the new branch if successful, empty string otherwise.
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # Sanitize task description for a valid branch name
        sanitized_task_name = "".join(c for c in task_description if c.isalnum() or c == "-").lower()
        if not sanitized_task_name:
            sanitized_task_name = "unnamed-feature"
        
        self._feature_branch_name = f"feature/{sanitized_task_name[:30].strip('-')}-{timestamp}" # type: ignore
        
        print(f"Attempting to create feature branch: {self._feature_branch_name} from base branch: {self._base_branch}") # type: ignore
        result = create_branch(self.base_branch, self.feature_branch_name) # type: ignore
        if result:
            print(f"Successfully created feature branch: {self._feature_branch_name}") # type: ignore
            return self._feature_branch_name # type: ignore
        else:
            print(f"Failed to create feature branch: {self._feature_branch_name}") # type: ignore
            self._feature_branch_name = None # Reset if creation failed # type: ignore
            return ""

    def create_pr(self, title: str, body: str) -> Optional[str]:
        """
        Creates a pull request from the active feature branch to the base branch.

        Args:
            title (str): The title of the pull request.
            body (str): The body/description of the pull request.

        Returns:
            str: The URL of the created pull request if successful, None otherwise.
        """
        if self._feature_branch_name: # type: ignore
            print(f"Attempting to create pull request from {self._feature_branch_name} to {self._base_branch}") # type: ignore
            pr_url = create_pull_request(title, body, self._feature_branch_name, self._base_branch) # type: ignore
            if pr_url:
                print(f"Pull Request created: {pr_url}")
                self._feature_branch_name = None # Reset after PR # type: ignore
                return pr_url
            else:
                print("Failed to create pull request.")
                return None
        else:
            print("No active feature branch to create a pull request from.")
            return None

developer_agent = DeveloperAgent(
    name="developer_agent",
    description="A developer agent that can plan and execute code changes after user approval.",
    instruction=DEVELOPER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    # sub_agents and tools are now managed within the DeveloperAgent's __init__
)

master_agent = Agent(
    name="personal_clone",
    description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
    instruction=MASTER_AGENT_INSTRUCTION,
    model=MASTER_AGENT_MODEL,
    tools=[
        get_current_date,
        write_to_rag,
        read_from_rag,
        update_in_rag,
        delete_from_rag,
        find_experiences,
        search_agent_tool,
        clickup_api.get_tasks,
        clickup_api.create_task,
        clickup_api.close_task,
        AgentTool(agent=developer_agent),
    ],
)

root_agent = master_agent
