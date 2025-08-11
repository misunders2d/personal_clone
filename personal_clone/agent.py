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
from .instructions import (
    DEVELOPER_AGENT_INSTRUCTION, 
    MASTER_AGENT_INSTRUCTION,
    CODE_REVIEWER_AGENT_INSTRUCTION,
    PLAN_REFINER_AGENT_INSTRUCTION,
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
    ],
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

# --- Workflow Agents ---

plan_and_review_agent = SequentialAgent(
    name="plan_and_review_agent",
    description="A workflow that creates a plan, then iteratively reviews and refines it.",
    sub_agents=[
        LoopAgent(name="review_loop",sub_agents=[planner_agent, code_reviewer_agent],
            max_iterations=5),
        plan_refiner_agent
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
