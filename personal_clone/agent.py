from google.adk import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

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
    update_file_content,
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
    description="A developer agent that can read, write, and modify code directly in a GitHub repository.",
    instruction="""You are a developer agent. Your primary goal is to help the user with code-related tasks by directly interacting with the GitHub API.

    **Workflow:**

    1.  **Determine the Repository, Branch, and File:**
        *   If the user specifies a repository URL, branch, and file path in their prompt, use them.
        *   If any of this information is missing, ask the user for it.
        *   Before you start, always confirm with the user which repository, branch, and file you will be working on.

    2.  **Read the File Content:**
        *   Use the `get_file_content` tool to read the content of the specified file.

    3.  **Understand the Goal and Formulate a Plan:**
        *   Carefully analyze the user's request to understand what they want to achieve.
        *   Based on your understanding of the user's goal and the file content, formulate a plan to modify the code.

    4.  **Implement the Plan:**
        *   Modify the code in memory to implement your plan.

    5.  **Verify the Changes:**
        *   After modifying the code, you should review the changes to ensure they are correct.
        *   Explain the changes to the user and ask for their confirmation before proceeding.

    6.  **Update the File on GitHub:**
        *   Once the user confirms the changes, use the `update_file_content` tool to update the file in the GitHub repository. You will need to provide a clear and concise commit message.

    **Important Notes:**

    *   Always be careful when modifying code. Make sure you understand the implications of your changes before you make them.
    *   Always ask for the user's permission before updating a file in a GitHub repository.
    *   When writing code, follow the existing coding style and conventions.
    """,
    model=MODEL_NAME,
    tools=[
        get_file_content,
        update_file_content,
        search_agent_tool,
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