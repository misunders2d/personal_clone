from google.adk import Agent
from google.adk.planners import BuiltInPlanner#, PlanReActPlanner
from google.genai import types

from ..tools.clickup_tools import clickup_toolset  # create_clickup_toolset
from ..callbacks.before_after_agent import professional_agents_checker

from .. import config

MODEL = config.FLASH_MODEL
PLANNER = (
    BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)
    )
    # if isinstance(MODEL, str)
    # else PlanReActPlanner()
)


def create_clickup_agent(name="clickup_agent"):
    """Creates an agent for interacting with ClickUp."""
    clickup_agent = Agent(
        name=name,
        description="An agent that manages ClickUp tasks. All user requests relating to clickup should be handled by this agent.",
        model=MODEL,
        instruction="""
        Use the tools available to you to answer user questions and manage tasks in ClickUp. The user info is stored in {clickup_user_info} session key.
        The user's email is stored in {user_id} session key.
        The current date and time are store in {current_datetime} key. Always refer to this key for be aware of the current date and time.
        Always use the `get_clickup_user` tool if you are missing any crucial ClickUp information.
        Don't bother the user with technical questions about ClickUp, use the tools to get the information you need.
        Only engage the user if you are missing information that you cannot get from ClickUp directly.
        When creating a new task - always confirm the creation with the task link (url)
        """,
        # tools=[create_clickup_toolset()],
        tools=clickup_toolset,
        planner=PLANNER,
        before_agent_callback=professional_agents_checker,
    )
    return clickup_agent
