import os
import json
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

try:
    import streamlit as st
    MASTER_AGENT_MODEL = st.secrets.get("MASTER_AGENT_MODEL", "")
    AUTHORIZED_USER_IDS = [x.strip() for x in st.secrets.get("AUTHORIZED_USERS", [])]
    os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = str(st.secrets.get("GOOGLE_GENAI_USE_VERTEXAI", ''))
    os.environ['GOOGLE_CLOUD_PROJECT'] = st.secrets.get("GOOGLE_CLOUD_PROJECT", '')
    os.environ['GOOGLE_CLOUD_LOCATION'] = st.secrets.get("GOOGLE_CLOUD_LOCATION", '')
except:
    MASTER_AGENT_MODEL = os.environ.get("MASTER_AGENT_MODEL", "")
    AUTHORIZED_USER_IDS = [x.strip() for x in os.environ["AUTHORIZED_USERS"].split(",")]



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


# --- Authorization Callback ---
# This is a list of user IDs that are allowed to access this agent.
# In a production system, you would load this from a secure database or user management service.


def check_user_authorization(callback_context: CallbackContext) -> types.Content | None:
    """
    Checks if the user is authorized to access the agent.

    This callback runs before the agent's main logic. It inspects the user_id
    from the session and checks it against a predefined list of authorized users.

    Args:
        callback_context: The context object provided by the ADK framework.

    Returns:
        A `types.Content` object with an error message if the user is not
        authorized, which stops agent execution.
        `None` if the user is authorized, allowing the agent to proceed.
    """
    user_id = callback_context.state.get("user_id")
    print(f"Auth Callback: Checking authorization for user_id: '{user_id}'")

    if user_id not in AUTHORIZED_USER_IDS:
        print(f"Auth Callback: User '{user_id}' is NOT AUTHORIZED.")
        # Returning a Content object stops the agent and sends this message back.
        return types.Content(
            parts=[
                types.Part(
                    text="Access Denied: You are not authorized to use this agent."
                )
            ]
        )

    print(f"Auth Callback: User '{user_id}' is authorized.")
    # Returning None allows the agent execution to continue.
    return None


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
        model=MASTER_AGENT_MODEL,
        sub_agents=[create_developer_agent(), create_financial_analyst_agent()],
        tools=[
            create_search_agent_tool("master_search_agent"),
            load_web_page,
            get_current_date,
            create_rag_agent_tool(),
            create_clickup_agent_tool(),
            AgentTool(agent=create_bigquery_agent()),
            AgentTool(agent=create_data_analyst_agent()),
        ],
        before_agent_callback=[load_adk_docs_to_session],
    )
    return master_agent


root_agent = create_master_agent()
