from google.adk.agents import Agent
from google.adk.tools.bigquery import bigquery_toolset
from .sub_agents.memory_agent import memory_agent
from .sub_agents.rag_agent import rag_agent

from dotenv import load_dotenv
load_dotenv()


def get_current_datetime():
    from datetime import datetime
    return datetime.now().isoformat()



root_agent = Agent(
    model='gemini-2.5-flash',
    name='personal_clone',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    sub_agents=[memory_agent, rag_agent],
    tools=[get_current_datetime]
)
