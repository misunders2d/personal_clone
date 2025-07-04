# Plan: Decoupled ClickUp Integration

This plan outlines the steps to integrate ClickUp functionality into the agent, keeping it separate from the core memory system (`search.py`) but allowing the agent to orchestrate interactions between the two.

### 1. Configuration Setup

-   **Update `.env.example`:** Add the following new variables:
    -   `CLICKUP_API_TOKEN`: For authenticating with the ClickUp API.
    -   `CLICKUP_SPACE_ID`: The ID of the target ClickUp Space.
    -   `CLICKUP_LIST_ID`: The ID of the target List within the Space.
    -   `CLICKUP_USER_EMAIL`: The email address for assigning tasks.

-   **Update `requirements.txt`:** Add the `requests` library to handle API calls to ClickUp.

### 2. Create a Standalone ClickUp Utility Module

-   Create a new file: `personal_clone/clickup_utils.py`.
-   This module will encapsulate all direct communication with the ClickUp API.
-   It will contain functions that the agent can call, such as:
    -   `get_tasks(list_id, email)`: To fetch assigned tasks.
    -   `create_task(list_id, title, description, email)`: To create a new task.
    -   `close_task(task_id)`: To change a task's status to "complete" or similar.

### 3. Modify the Memory System (`search.py`) for Optional Linking

-   To handle cases where a memory needs to be linked to a task, the `write_to_rag` and `update_in_rag` functions will be modified.
-   Add an optional `clickup_task_id: Optional[str] = None` parameter to both functions.
-   If this parameter is provided, the function will add `clickup_task_id: <id>` to the memory's metadata. Otherwise, it will be omitted. This allows for traceability without creating a hard dependency.

### 4. Enhance the Agent (`agent.py`) as the Orchestrator

-   The agent will be the central component that understands user intent and calls the appropriate utility functions.
-   **Intent Handling Examples:**
    -   **User:** "What are my todos?" -> **Agent calls:** `clickup_utils.get_tasks()`
    -   **User:** "Remember that I prefer morning meetings." -> **Agent calls:** `search.py`'s `write_to_rag()`
    -   **User:** "Create a task to review the quarterly report and save a note about it." -> **Agent performs a two-step action:**
        1.  Calls `clickup_utils.create_task()`.
        2.  Receives the new task ID from the response.
        3.  Calls `search.py`'s `write_to_rag()`, passing the note content and the `clickup_task_id` to link them.
