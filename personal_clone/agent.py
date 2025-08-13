from google.adk.agents import Agent, SequentialAgent, LoopAgent, ParallelAgent
from google.adk.tools import google_search, exit_loop
from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp import MCPToolset

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
    BRANCH_NAME,  # Import the default branch name
)
from .instructions import (
    DEVELOPER_AGENT_INSTRUCTION,
    MASTER_AGENT_INSTRUCTION,
    CODE_REVIEWER_AGENT_INSTRUCTION,
    PLANNER_AGENT_INSTRUCTION,
)

# --- Constants ---
SEARCH_MODEL_NAME = "gemini-2.5-flash"
MODEL_NAME = "gemini-2.5-flash"
MASTER_AGENT_MODEL = "gemini-2.5-pro"
COINGECKO_MCP_HOST = "https://mcp.api.coingecko.com/sse"

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

    return {"kiev_time": kiev_formatted, "new_york_time": new_york_formatted}


def create_search_agent_tool(name="web_search_agent"):
    search_agent_tool = AgentTool(
        agent=Agent(
            name=name,
            description="A web search agent that can search the web and find information.",
            instruction="You are a web search agent. Use the `google_search` tool to find relevant information online.",
            tools=[google_search],
            model=SEARCH_MODEL_NAME,
        ),
        skip_summarization=True,
    )
    return search_agent_tool


# --- Developer Workflow Sub-Agents ---


def create_planner_agent(name="planner_agent", output_key="development_plan"):
    planner_agent = Agent(
        name=name,
        description="Creates and refines development plans.",
        instruction=PLANNER_AGENT_INSTRUCTION,
        model=MODEL_NAME,
        tools=[
            create_search_agent_tool(),
            list_repo_files,
            get_file_content,
            exit_loop,
            load_web_page,
        ],
        output_key=output_key,
    )
    return planner_agent


def create_code_reviewer_agent(
    name="code_reviewer_agent", output_key="reviewer_feedback"
):
    code_reviewer_agent = Agent(
        name=name,
        description="Reviews development plans for quality and adherence to project standards.",
        instruction=CODE_REVIEWER_AGENT_INSTRUCTION,
        model=LiteLlm("openai/gpt-4.1-nano"),
        tools=[
            get_file_content,
            list_repo_files,
            create_search_agent_tool(),
            load_web_page,
        ],
        output_key=output_key,
    )
    return code_reviewer_agent


def create_plan_fetcher_agent(
    name="plan_fetcher_agent", session_key="development_plan"
):
    plan_fetcher_agent = Agent(
        name=name,
        description="Refines development plans based on reviewer feedback.",
        instruction=f'''
Your only job is to fetch the approved development plan from the st.session_state['{session_key}'].
DO NOT MODIFY THE PLAN IN ANY WAY. OUTPUT THE PLAN AS IS.
If the st.session_state['{session_key}'] key is empty - you must convey this explicitly: "The {session_key} has not been developed"
''',
        model=MODEL_NAME,
        tools=[],
    )
    return plan_fetcher_agent


# --- Workflow Agents ---


def create_code_review_loop(
    name="review_loop",
    planner_name="planner_agent",
    planner_output="development_plan",
    code_reviewer_name="code_reviewer_agent",
    code_reviewer_output="reviewer_feedback",
):
    code_review_loop = LoopAgent(
        name=name,
        description="A loop agent that creates and reviews development plans iteratively to achieve best results.",
        sub_agents=[
            create_planner_agent(planner_name, planner_output),
            create_code_reviewer_agent(code_reviewer_name, code_reviewer_output),
        ],
        max_iterations=10,
    )
    return code_review_loop


def create_planner_sequence(n=1):
    planner_sequence = SequentialAgent(
        name=f"planner_sequence_{n}",
        description="An agent that creates a development plan and reviews it iteratively until approved.",
        sub_agents=[
            create_code_review_loop(
                name=f"review_loop_{n}",
                planner_name=f"planner_agent_{n}",
                planner_output=f"development_plan_{n}",
                code_reviewer_name=f"code_reviewer_agent_{n}",
                code_reviewer_output=f"reviewer_feedback_{n}",
            ),
            create_plan_fetcher_agent(
                name=f"plan_fetcher_agent_{n}", session_key=f"development_plan_{n}"
            ),
        ],
    )
    return planner_sequence


def plan_and_review_agent():
    plan_and_review_agent = ParallelAgent(
        name="plan_and_review_agent",
        description="An agent that runs multiple code planning and review processes in parallel and outputs all plans",
        sub_agents=[create_planner_sequence(1), create_planner_sequence(2)],
    )
    return plan_and_review_agent


# --- Primary User-Facing Agents ---


def create_financial_analyst_agent(name="financial_analyst_agent"):
    """
    Creates an ADK Agent capable of providing cryptocurrency buy/sell recommendations
    for Ton, Ethereum, and Bitcoin using the CoinGecko MCP Server.
    """
    coingecko_toolset = MCPToolset(
        host=COINGECKO_MCP_HOST,
        tool_filter=[
            "get_price",  # Assumed tool name for getting current price
            "get_historical_data", # Assumed tool name for getting historical data
            # Add other specific CoinGecko MCP tool names as confirmed by documentation
        ]
    )

    financial_analyst_agent = Agent(
        name=name,
        description="Provides cryptocurrency buy/sell recommendations for Ton, Ethereum, and Bitcoin.",
        instruction='''
        You are a Financial Analyst Agent. Your primary role is to provide cryptocurrency buy, sell, or hold
        recommendations for Ton, Ethereum, and Bitcoin.

        To formulate your recommendations:
        1. Use the CoinGecko tools to fetch the *current price* of Ton, Ethereum, and Bitcoin.
        2. Use the CoinGecko tools to fetch *historical price data* (e.g., last 24 hours, 7 days) for these cryptocurrencies
           to identify recent trends.
        3. Based on the current price and recent trends:
           - If a cryptocurrency's price has shown a significant upward trend (e.g., >5% increase in 24 hours),
             recommend 'Hold' or 'Consider Selling' if it's already high.
           - If a cryptocurrency's price has shown a significant downward trend (e.g., >5% decrease in 24 hours),
             recommend 'Consider Buying' or 'Hold'.
           - If the price is relatively stable, recommend 'Monitor'.
           - Always clearly state the current price as part of your recommendation.
        4. If a user asks for a cryptocurrency not explicitly mentioned (Ton, Ethereum, Bitcoin),
           kindly inform them that your analysis is limited to these three, but you can still fetch their current price.
        5. Provide clear, concise, and actionable recommendations.
        6. Handle cases where data for a specific cryptocurrency might be temporarily unavailable gracefully by
           stating the limitation.
        ''',
        model=MODEL_NAME, # Use the existing MODEL_NAME from agent.py
        tools=[
            coingecko_toolset,
        ],
    )
    return financial_analyst_agent


def create_developer_agent():
    developer_agent = Agent(
        name="developer_agent",
        description="A developer agent that can plan and execute code changes after user approval.",
        instruction=DEVELOPER_AGENT_INSTRUCTION,
        model=MODEL_NAME,
        sub_agents=[plan_and_review_agent()],
        tools=[
            create_branch,
            create_or_update_file,
            create_pull_request,
            list_repo_files,
            get_file_content,
            load_web_page
        ],
    )
    return developer_agent


def create_master_agent():
    master_agent = Agent(
        name="personal_clone",
        description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
        instruction=MASTER_AGENT_INSTRUCTION,
        model=MASTER_AGENT_MODEL,
        tools=[
            create_search_agent_tool('master_search_agent'),
            load_web_page,
            get_current_date,
            write_to_rag,
            read_from_rag,
            update_in_rag,
            delete_from_rag,
            find_experiences,
            create_search_agent_tool(),
            clickup_api.get_tasks,
            clickup_api.create_task,
            clickup_api.close_task,
            AgentTool(agent=create_developer_agent()),
            AgentTool(agent=create_financial_analyst_agent()), # Add this line
        ],
    )
    return master_agent


root_agent = create_master_agent()