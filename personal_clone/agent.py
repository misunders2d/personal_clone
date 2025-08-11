from google.adk.agents import Agent, SequentialAgent, LoopAgent
from google.adk.tools import google_search, exit_loop
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm

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

# --- Ancillary Services & Tools ---
clickup_api = ClickUpAPI()

def get_current_date():
    """Returns the current date and time in YYYY-MM-DD HH:MM:SS format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

# --- Planning and Review Workflow ---

plan_and_review_agent = SequentialAgent(
    name="plan_and_review_agent",
    description="A workflow that creates a plan, then iteratively reviews and refines it.",
    sub_agents=[
        planner_agent,
        LoopAgent(name="review_loop",sub_agents=[code_reviewer_agent,plan_refiner_agent],
            max_iterations=5,)
    ]
)

# --- Primary Developer Agent ---

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

# --- Master Agent ---

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
    ],
)

root_agent = master_agent