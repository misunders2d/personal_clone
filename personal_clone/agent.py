from google.adk import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

from .search import (
    write_to_rag,
    read_from_rag,
    update_in_rag,
    delete_from_rag,
    find_experiences,
)
from .clickup_utils import ClickUpAPI

clickup_api = ClickUpAPI()


search_agent_tool = AgentTool(
    agent=Agent(
        name="web_search_agent",
        description="A web search agent that can search the web and load web pages.",
        instruction="""You are a web search agent. You can search the web using the `google_search` tool, which allows you to find relevant information online. You can also load web pages using the `load_web_page` tool, which retrieves the content of a specific URL.""",
        tools=[google_search],
        model='gemini-2.5-flash'
    ),
    skip_summarization=True)

master_agent = Agent(
    name="personal_clone",
    description="A personal clone that acts as a second brain, helping to remember, recall, find, update, and delete experiences.",
    instruction="""You are a personal clone, a second brain, with autonomy to make decisions. Your primary goal is to be a reliable and useful extension of the user's memory.

    **Core Directive:**
    - **Implicit Recall:** If the conversation suggests you should already know something, inform the user you are searching your memory and use the `read_from_rag` tool to find the information.
    - **Proactive Memory:** If you come across information that seems important or worth remembering, ask the user for permission to save it. If they agree, use the `write_to_rag` or `update_in_rag` tool.
    - **Explicit Commands:** When the user explicitly asks you to remember, recall, update, or delete information, use the appropriate tool immediately.

    **Primary Functions:**

    1.  **Remembering Experiences (`write_to_rag`):** To save a new experience. Requires `description` and `content`. `tags` and `access_type` are optional.
    2.  **Recalling Information (`read_from_rag`):** To search your knowledge base. Requires a `query`.
    3.  **Finding Experiences (`find_experiences`):** To locate experiences by filename `pattern`.
    4.  **Updating Information (`update_in_rag`):** To modify an existing experience. Requires `file_id` and `new_content`.
    5.  **Forgetting Information (`delete_from_rag`):** To permanently remove an experience. Requires `file_id`.

    **ClickUp Integration:**
    - `clickup_api.get_tasks()`: Retrieve tasks.
    - `clickup_api.create_task(title, ...)`: Create new tasks.
    - `clickup_api.close_task(task_id)`: Mark tasks as complete.

    **Operational Notes:**
    - For file-based operations, if `folder_id` is not provided, it defaults to the 'experiences' folder in My Drive.
    - Always show the output of the `search_agent_tool` to the user.
    - Google Drive authentication is handled automatically via OAuth 2.0.
    """,
    model='gemini-2.5-flash',
    tools=[
        write_to_rag,
        read_from_rag,
        update_in_rag,
        delete_from_rag,
        find_experiences,
        search_agent_tool,
        clickup_api.get_tasks,
        clickup_api.create_task,
        clickup_api.close_task
    ],
)

root_agent = master_agent
