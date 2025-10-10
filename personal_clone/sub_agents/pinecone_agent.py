from google.adk import Agent

from ..tools.pinecone_tools import create_pinecone_toolset
from ..callbacks.before_after_agent import professional_agents_checker

from .. import config


def create_pinecone_agent(name="pinecone_agent"):
    """Creates an agent for interacting with Pinecone database."""
    pinecone_agent = Agent(
        name=name,
        description="An agent that manages Pinecone requests. All user requests relating to Pinecone should be handled by this agent.",
        model=config.PINECONE_AGENT_MODEL,
        instruction="""
        Use the tools available to you to answer user questions and manage tasks in Pinecone. The user info is stored in {clickup_user_info} session key.
        The user's email is stored in {user_id} session key.
        The current date and time are store in {current_datetime} key. Always refer to this key for be aware of the current date and time.
        """,
        tools=[create_pinecone_toolset()],
        planner=config.PINECONE_AGENT_PLANNER,
        before_agent_callback=professional_agents_checker,
    )
    return pinecone_agent
