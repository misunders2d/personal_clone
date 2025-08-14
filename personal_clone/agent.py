from google.adk.agents import Agent, SequentialAgent, LoopAgent, ParallelAgent

from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.agent_tool import AgentTool

import os

from sub_agents.search_agent import create_search_agent_tool
from sub_agents.financial_analyst import create_financial_analyst_agent
from sub_agents.developer_agent import create_developer_agent

from utils.search import (
    write_to_rag,
    read_from_rag,
    update_in_rag,
    delete_from_rag,
    find_experiences,
)

from utils.datetime_utils import get_current_date

from instructions import MASTER_AGENT_INSTRUCTION

from utils.clickup_utils import ClickUpAPI

clickup_api = ClickUpAPI()


def create_master_agent():
    master_agent = Agent(
        name="personal_clone",
        description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
        instruction=MASTER_AGENT_INSTRUCTION,
        model=os.environ["MASTER_AGENT_MODEL"],
        tools=[
            create_search_agent_tool("master_search_agent"),
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
            AgentTool(agent=create_financial_analyst_agent()),  # Add this line
        ],
    )
    return master_agent
