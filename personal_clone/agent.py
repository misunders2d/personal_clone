from google.adk.agents import Agent

from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.agent_tool import AgentTool

import os

from .sub_agents.search_agent import create_search_agent_tool
from .sub_agents.financial_analyst import create_financial_analyst_agent
from .sub_agents.bigquery_agent import create_bigquery_agent
from .coding_agents.developer_agent import create_developer_agent
from .sub_agents.data_analyst_agent import create_data_analyst_agent

from .sub_agents.rag_agent import create_rag_agent_tool
from .sub_agents.clickup_agent import create_clickup_agent_tool
from .utils.datetime_utils import get_current_date
from .instructions import MASTER_AGENT_INSTRUCTION


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
            create_rag_agent_tool(),
            create_clickup_agent_tool(),
            AgentTool(agent=create_developer_agent()),
            AgentTool(agent=create_financial_analyst_agent()),
            AgentTool(agent=create_bigquery_agent()),
            AgentTool(agent=create_data_analyst_agent()),
        ],
    )
    return master_agent
