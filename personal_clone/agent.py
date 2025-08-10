from google.adk import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm

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
)
from .instructions import DEVELOPER_AGENT_INSTRUCTION, MASTER_AGENT_INSTRUCTION

# Define the model name as a constant
# MODEL_NAME = 'gemini-2.0-flash-live-001'
SEARCH_MODEL_NAME='gemini-2.5-flash'
# MODEL_NAME='gemini-live-2.5-flash-preview-native-audio'
MODEL_NAME='gemini-2.5-flash'

clickup_api = ClickUpAPI()

def get_current_date():
    """Returns the current date and time in YYYY-MM-DD HH:MM:SS format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

search_agent_tool = AgentTool(
    agent=Agent(
        name="web_search_agent",
        description="A web search agent that can search the web and load web pages.",
        instruction="""You are a web search agent. You can search the web using the `google_search` tool, which allows you to find relevant information online. You can also load web pages using the `load_web_page` tool, which retrieves the content of a specific URL.""",
        tools=[google_search],
        model=SEARCH_MODEL_NAME
    ),
    skip_summarization=True)

developer_agent = Agent(
    name="developer_agent",
    description="A developer agent that can read, write, and modify code directly in the 'development' GitHub branch.",
    instruction=DEVELOPER_AGENT_INSTRUCTION,
    # model=LiteLlm(model="openai/gpt-4.1-nano"),
    model=MODEL_NAME,
    tools=[
        search_agent_tool,
        list_repo_files,
        get_file_content,
        create_or_update_file,
    ],
)

master_agent = Agent(
    name="personal_clone",
    description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
    instruction=MASTER_AGENT_INSTRUCTION,
    model=MODEL_NAME,
    tools=[
        get_current_date,
        write_to_rag,
        read_from_rag,
        update_in_rag,
        delete_from_rag,
        find_experiences,
        search_agent_tool,
        clickup_api.get_tasks,
        clickup_api.create_task,
        clickup_api.close_task,
        AgentTool(agent=developer_agent),
    ],
)

root_agent = master_agent