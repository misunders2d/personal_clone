from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
import pytz

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
)
from .session_utils import get_session_events_as_json
from .instructions import (
    DEVELOPER_AGENT_INSTRUCTION, 
    MASTER_AGENT_INSTRUCTION,
    CODE_REVIEWER_AGENT_INSTRUCTION,
    PLAN_REFINER_AGENT_INSTRUCTION,
    PLANNER_AGENT_INSTRUCTION,
    SESSION_ANALYZER_INSTRUCTION
)

# --- Constants ---
SEARCH_MODEL_NAME='gemini-2.5-flash'
MODEL_NAME='gemini-2.5-flash'

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

code_reviewer_agent = Agent(
    name="code_reviewer_agent",
    description="Reviews development plans for quality and adherence to project standards.",
    instruction=CODE_REVIEWER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    tools=[
        get_file_content,
        list_repo_files,
        search_agent_tool,
        exit_loop,
    ],
)

plan_refiner_agent = Agent(
    name="plan_refiner_agent",
    description="Refines development plans based on reviewer feedback.",
    instruction=PLAN_REFINER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    tools=[],
)

planner_agent = Agent(
    name="planner_agent",
    description="Creates and refines development plans.",
    instruction=PLANNER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    tools=[
        search_agent_tool,
        list_repo_files,
        get_file_content,
    ],
)

# --- Specialist Agents ---

session_analyzer_agent = Agent(
    name="session_analyzer_agent",
    description="Analyzes the current session to diagnose issues and summarize behavior.",
    instruction=SESSION_ANALYZER_INSTRUCTION,
    model=MODEL_NAME,
    tools=[
        get_session_events_as_json,
        get_file_content, # To read instructions.py or other relevant files
    ]
)

# --- Workflow Agents ---

plan_and_review_agent = SequentialAgent(
    name="plan_and_review_agent",
    description="A workflow that creates a plan, then iteratively reviews and refines it.",
    sub_agents=[
        planner_agent,
        LoopAgent(name="review_loop",sub_agents=[code_reviewer_agent,plan_refiner_agent],
            max_iterations=5,)
    ]
)

# --- Primary User-Facing Agents ---

developer_agent = Agent(
    name="developer_agent",
    description="A developer agent that can plan and execute code changes after user approval.",
    instruction=DEVELOPER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    sub_agents=[plan_and_review_agent],
    tools=[
        create_or_update_file,
        get_file_content,
        list_repo_files,
        search_agent_tool,
    ],
)

master_agent = Agent(
    name="personal_clone",
    description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
    instruction=MASTER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
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
        AgentTool(agent=session_analyzer_agent),
    ],
)

root_agent = master_agent
