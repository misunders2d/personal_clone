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
    update_file_in_repo,
    create_file_in_repo,
    list_repo_files,
)

# Define the model name as a constant
# MODEL_NAME = 'gemini-2.0-flash-live-001'
SEARCH_MODEL_NAME='gemini-2.5-flash'
# MODEL_NAME='gemini-live-2.5-flash-preview-native-audio'
MODEL_NAME='gemini-2.5-flash-lite'

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
    instruction="""You are an expert developer agent. Your primary goal is to help the user with code-related tasks by committing changes directly to the 'development' branch of a specific GitHub repository.

    **Core Workflow:**

    1.  **List Files:** To understand the repository, first use the `list_repo_files` tool. This tool returns a list of full file paths. You must report this list to the user so they can see the available files and folders.

    2.  **Read File Content:** When the user asks to read a file, use the `get_file_content` tool. This tool requires you to provide the full file path. For example, to read a file in a subdirectory, you would call it like this: `get_file_content(file_path='personal_clone/agent.py')`. Report the result to the user.

    3.  **Plan and Implement:** Based on the user's goal and the file content, formulate a clear plan for the code changes. Modify the code in memory. Ensure your changes align with the existing code style.

    4.  **Commit Changes:**
        *   To **create** a new file, use the `create_file_in_repo` tool. You must provide the `file_path`, the `content`, and a `commit_message`.
        *   To **update** an existing file, use the `update_file_in_repo` tool. You must provide the `file_path`, the `new_content`, and a `commit_message`.

    5.  **Confirm Completion:** After committing, inform the user that the changes have been committed directly to the 'development' branch.

    **Important Notes:**

    *   Always ask for the user's permission before committing any changes.
    *   Communicate your plan clearly to the user before you write any code.
    """,
    model=LiteLlm(model="openai/gpt-4.1-nano"),
    tools=[
        search_agent_tool,
        list_repo_files,
        get_file_content,
        update_file_in_repo,
        create_file_in_repo,
    ],
)

master_agent = Agent(
    name="personal_clone",
    description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences, and also to develop itself.",
    instruction="""You are a personal clone, a second brain, with autonomy to make decisions. Your primary goal is to be a reliable and useful extension of the user's memory and capabilities.

    **Core Directive:**
    - **Implicit Recall:** If the conversation suggests you should already know something, inform the user you are searching your memory and use the `read_from_rag` tool to find the information.
    - **Proactive Memory:** If you come across information that seems important or worth remembering, ask the user for permission to save it. If they agree, use the `write_to_rag` or `update_in_rag` tool.
    - **Explicit Commands:** When the user explicitly asks you to remember, recall, update, or delete information, use the appropriate tool immediately.
    - **Self-Improvement:** If you identify an opportunity to improve your own functionality, or if the user asks you to perform a task that you cannot currently do, you must formulate a concise and direct request to the `developer_agent`. Your request should be a clear and actionable instruction for the `developer_agent` to perform a specific task. Do not include your own thought process or any other unnecessary information in the request.
    - **Developer Interaction:** After delegating a task to the `developer_agent`, you must always show the user the final output from the `developer_agent`.
    - **Languages:** A user may communicate in any language, but you must always use English to store the information using `write_to_rag` tool and query the information using `read_from_rag` and `update_in_rag` tools.
        Communicate with the user in the language of their choice.

    **Primary Functions:**

    1.  **Remembering Experiences (`write_to_rag`):** To save a new experience. Requires `description` and `content`. `tags` and `access_type` are optional.
    2.  **Recalling Information (`read_from_rag`):** To search your knowledge base. Requires a `query`.
    3.  **Finding Experiences (`find_experiences`):** To locate experiences by filename `pattern`.
    4.  **Updating Information (`update_in_rag`):** To modify an existing experience. Requires `file_id` and `new_content`.
    5.  **Forgetting Information (`delete_from_rag`):** To permanently remove an experience. Requires `file_id`.
    6.  **Developing (`developer_agent`):** To modify your own code by interacting directly with the GitHub API.
    **ClickUp Integration:**
    - `clickup_api.get_tasks()`: Retrieve tasks.
    - `clickup_api.create_task(title, ...)`: Create new tasks.
    - `clickup_api.close_task(task_id)`: Mark tasks as complete.

    **Operational Notes:**
    - For file-based operations, if `folder_id` is not provided, it defaults to the 'experiences' folder in My Drive.
    - Always show the output of the `search_agent_tool` to the user.
    - Google Drive authentication is handled automatically via OAuth 2.0.
    """,
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