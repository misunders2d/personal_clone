from google.adk.agents import Agent
from google.adk.tools import AgentTool

from ..utils.clickup_utils import ClickUpAPI
from .rag_agent import create_rag_agent_tool

import os

clickup_api = ClickUpAPI()

def create_clickup_agent_tool(name="clickup_agent"):
    clickup_agent = Agent(
        name=name,
        description="An agent that manages ClickUp tasks and can link them to experiences.",
        instruction='''
You are a ClickUp agent. You can create, get, and close tasks in ClickUp.
You can also create an experience in the RAG system and link it to a ClickUp task.
To do this, you need to use the `rag_agent` tool.
First, create the ClickUp task using `create_task`.
Then, use the `rag_agent.write_to_rag` tool to create the experience, passing the `clickup_task_id` from the created task.
''',
        model=os.environ["MODEL_NAME"],
        tools=[
            clickup_api.get_tasks,
            clickup_api.create_task,
            clickup_api.close_task,
            create_rag_agent_tool("rag_agent_for_clickup"),
        ],
    )
    return AgentTool(agent=clickup_agent)