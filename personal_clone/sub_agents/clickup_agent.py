from google.adk import Agent

from ..tools.clickup_tools import get_clickup_user


def create_clickup_agent(name="clickup_agent"):
    """Creates an agent for interacting with ClickUp."""
    clickup_agent = Agent(
        name=name,
        description="An agent that manages ClickUp tasks. All user requests relating to clickup should be handled by this agent.",
        model="gemini-2.0-flash-lite",
        instruction="""Use the tools available to you to answer user questions and manage tasks in ClickUp.
        """,
        tools=[get_clickup_user],
    )
    return clickup_agent
