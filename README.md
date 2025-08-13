# personal_clone

`personal_clone` is an agentic system designed to act as a "second brain," remembering and accumulating your experiences, memories, and interaction details. It leverages Google Drive for durable storage and Pinecone for powerful retrieval-augmented generation (RAG) capabilities.

## Core Functionality

The agent provides five primary functions to manage your knowledge base:

1.  **Remembering Experiences (`write_to_rag`)**:
    *   **Purpose**: To save a new experience into your knowledge base.
    *   **Usage**: Provide a `description`, the `content` of the experience, an optional list of `tags`, an optional `access_type` (either "private" or "public"), and an optional `folder_id`.
    *   **Output**: Returns the `file_id` of the newly created experience in Google Drive.

2.  **Recalling Information (`read_from_rag`)**:
    *   **Purpose**: To search your knowledge base for relevant information based on content. This function performs a semantic search using Pinecone.
    *   **Usage**: Provide a clear `query`. You can also filter by `access_type` and `folder_id`.
    *   **Output**: Returns a list of dictionaries. Each dictionary contains the `file_id`, `file_name`, `content`, `description`, `tags`, and `access_type` of the relevant experience. This `file_id` is crucial for subsequent update or delete operations.

3.  **Finding Experiences (`find_experiences`)**:
    *   **Purpose**: To locate experiences based on patterns in their filenames. This is useful when you know part of the filename or a specific naming convention.
    *   **Usage**: Provide a `pattern` (e.g., `experience_202507*.txt`) to match against file names in Google Drive. You can also specify a `folder_id`.
    *   **Output**: Returns a list of dictionaries. Each dictionary provides detailed information about the matching experience, including its `file_id`, `file_name`, `description`, `tags`, `access_type`, and a `content_snippet` for easy identification.

4.  **Updating Information (`update_in_rag`)**:
    *   **Purpose**: To modify an existing experience.
    *   **Usage**: Requires the exact `file_id` of the experience (obtained from `read_from_rag` or `find_experiences`), the `new_content` to overwrite the old, an optional list of `new_tags`, an optional `new_access_type`, and an optional `folder_id`.
    *   **Output**: A confirmation message upon successful update.

5.  **Forgetting Information (`delete_from_rag`)**:
    *   **Purpose**: To permanently remove an experience from your knowledge base.
    *   **Usage**: Requires the exact `file_id` of the experience (obtained from `read_from_rag` or `find_experiences`) and an optional `folder_id`.
    *   **Output**: A confirmation message upon successful deletion.

6.  **ClickUp Integration**:
    *   **Purpose**: To manage tasks within ClickUp directly from the agent.
    *   **`get_tasks()`**: Retrieves tasks from your configured ClickUp list. Tasks will include their due dates.
    *   **`create_task(title, description=None, due_date=None, start_date=None)`**: Creates a new task in your configured ClickUp list. `description`, `due_date` (Unix timestamp in milliseconds), and `start_date` (Unix timestamp in milliseconds) are optional.
    *   **`close_task(task_id)`**: Marks a ClickUp task as complete.

7.  **Self-Development (`developer_agent`)**:
    *   **Purpose**: To evolve the agent's own capabilities by modifying its source code.
    *   **Usage**: You can ask the agent to fix bugs, add new tools, or refactor its code. The `developer_agent` will handle the request.
    *   **Workflow**: The agent follows a rigorous internal process to ensure changes are safe and well-designed. It first creates a detailed development plan, which is then reviewed and refined by specialized sub-agents in an iterative loop. This approved plan is then presented to you for final confirmation before any code is written to the repository.

## Autonomous Operation

The agent is designed to be more than just a passive tool. It has the autonomy to make decisions and take initiative:

*   **Implicit Recall**: If a conversation implies that the agent should have prior knowledge of a topic, it will automatically search its memory and inform you of its findings.
*   **Proactive Memory**: If the agent identifies information that could be valuable to remember, it will ask for your permission to save it to your knowledge base.
*   **Explicit Commands**: The agent will always prioritize your direct commands to remember, recall, update, or delete information.

## Streamlit UI

The user interface for `personal_clone` is built with Streamlit. It provides a chat-based interface for interacting with the agent. The UI is defined in `main.py` and uses various Streamlit components to create a seamless user experience.

## Technology Stack

*   **Agent Framework**: Google ADK (Agent Development Kit)
*   **UI Framework**: Streamlit
*   **Storage**: Google Drive for storing raw experience files.
*   **Search & Retrieval**: Pinecone for indexing and semantic search capabilities.

## Important Notes on File IDs and File Names

The `file_id` is a critical identifier for `update_in_rag` and `delete_from_rag`.
*   `write_to_rag` generates and returns this `file_id`.
*   `read_from_rag` now returns the `file_id` and `file_name` for each relevant search result, allowing you to directly use the `file_id` for management operations.
*   `find_experiences` also returns the `file_id` and `file_name` for experiences matching filename patterns.

## Google Drive Authentication

This agent uses a Google Cloud service account for authentication with Google Drive. This method is more secure and better suited for applications running on a server. The service account key is stored securely in Streamlit secrets.

## Setup

To get `personal_clone` up and running, follow these steps:

### Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)

### Google Cloud Project Setup

1.  **Create a Google Cloud Project**: If you don't have one, create a new project in the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Enable Google Drive API**:
    *   In your Google Cloud Project, navigate to "APIs & Services" > "Library".
    *   Search for "Google Drive API" and enable it.
3.  **Create a Service Account**:
    *   In your Google Cloud Project, navigate to "IAM & Admin" > "Service Accounts".
    *   Click "Create Service Account".
    *   Give the service account a name (e.g., `personal-clone-gdrive`) and a description.
    *   Click "Create and Continue".
    *   Grant the service account the "Editor" role to allow it to create, edit, and delete files in Google Drive.
    *   Click "Continue".
    *   Click "Done".
4.  **Create a Service Account Key**:
    *   Find the service account you just created in the list.
    *   Click on the three dots under "Actions" and select "Manage keys".
    *   Click "Add Key" > "Create new key".
    *   Select "JSON" as the key type and click "Create".
    *   A JSON file with the service account key will be downloaded to your computer.
5.  **Share Google Drive Folder with Service Account**:
    *   Open the JSON key file you downloaded. You will find a `client_email` field.
    *   In Google Drive, create a folder where the agent will store its files.
    *   Share this folder with the service account's email address (`client_email`) and give it "Editor" permissions.
6.  **Set Streamlit Secret**:
    *   Open the JSON key file and copy its entire content.
    *   In your Streamlit Cloud project, go to "Settings" > "Secrets".
    *   Create a new secret with the name `gcp_service_account` and paste the JSON content as the value.

### Pinecone Setup

1.  **Create a Pinecone Account**: If you don't have one, sign up at [Pinecone](https://www.pinecone.io/).
2.  **Get API Key and Environment**:
    *   Once logged in, navigate to your API Keys section.
    *   Copy your `API Key` and `Environment` (e.g., `us-west-2-gcp`).
3.  **Set Environment Variables**:
    *   Add the following lines to your `.env` file:
        ```
        PINECONE_API_KEY="YOUR_PINECONE_API_KEY"
        PINECONE_ENVIRONMENT="YOUR_PINECONE_ENVIRONMENT"
        PINECONE_INDEX_NAME="personal-clone-index" # Or your preferred index name
        ```

### ClickUp Setup

1.  **Get API Token, Space ID, List ID, and User Email**:
    *   **API Token**: Log in to ClickUp, click your profile avatar (bottom-left), go to "Apps" or "Integrations", and find "API Tokens" to generate and copy your token (starts with `pk_`).
    *   **Space ID**: Navigate to the desired Space in ClickUp. The Space ID is part of the URL (e.g., `.../v/s/YOUR_SPACE_ID/...`).
    *   **List ID**: Navigate to the desired List in ClickUp. The List ID is part of the URL (e.g., `.../list/YOUR_LIST_ID`).
    *   **User Email**: The email address associated with your ClickUp account that you want to assign tasks to.

2.  **Set Environment Variables**:
    *   Add the following lines to your `.env` file:
        ```
        CLICKUP_API_TOKEN="YOUR_CLICKUP_API_TOKEN"
        CLICKUP_SPACE_ID="YOUR_CLICKUP_SPACE_ID"
        CLICKUP_LIST_ID="YOUR_CLICKUP_LIST_ID"
        CLICKUP_USER_EMAIL="YOUR_CLICKUP_USER_EMAIL"
        ```

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/personal_clone.git
    cd personal_clone
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

To run the `personal_clone` application, execute the following command in your terminal:

```bash
streamlit run main.py
```

This will start the Streamlit development server and open the application in your web browser.

Now you are ready to use `personal_clone`!
