import os
import json
from google.adk.agents.callback_context import CallbackContext

from dotenv import load_dotenv

load_dotenv()


from google.adk.agents import Agent
from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.agent_tool import AgentTool

from .sub_agents.search_agent import create_search_agent_tool
from .sub_agents.financial_analyst import create_financial_analyst_agent
from .sub_agents.bigquery_agent import create_bigquery_agent
from .coding_agents.developer_agent import create_developer_agent
from .sub_agents.data_analyst_agent import create_data_analyst_agent

from .sub_agents.rag_agent import create_rag_agent_tool
from .sub_agents.clickup_agent import create_clickup_agent_tool
from .utils.datetime_utils import get_current_date
from .instructions import MASTER_AGENT_INSTRUCTION


# Callback to load ADK documentation into the session state.
def load_adk_docs_to_session(callback_context: CallbackContext):
    """Loads ADK documentation into the session state for easy reference."""
    if "official_adk_references" in callback_context.state:
        return  # Docs are already loaded

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load API reference
    json_path = os.path.join(script_dir, "..", "adk_metadata.json")
    with open(os.path.normpath(json_path)) as f:
        api_reference = json.load(f)

    # Load conceptual docs
    txt_path = os.path.join(script_dir, "..", "llms-full.txt")
    with open(os.path.normpath(txt_path)) as f:
        conceptual_docs = f.read()

    callback_context.state["official_adk_references"] = {
        "api_reference": api_reference,
        "conceptual_docs": conceptual_docs,
    }


def create_master_agent():
    master_agent = Agent(
        name="personal_clone",
        description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
        instruction=MASTER_AGENT_INSTRUCTION,
        model=os.environ["MASTER_AGENT_MODEL"],
        sub_agents=[create_developer_agent()],
        tools=[
            create_search_agent_tool("master_search_agent"),
            load_web_page,
            get_current_date,
            create_rag_agent_tool(),
            create_clickup_agent_tool(),
            AgentTool(agent=create_financial_analyst_agent()),
            AgentTool(agent=create_bigquery_agent()),
            AgentTool(agent=create_data_analyst_agent()),
        ],
        before_agent_callback=[load_adk_docs_to_session],
    )
    return master_agent


root_agent = create_master_agent()
