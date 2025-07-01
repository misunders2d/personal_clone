# personal_clone

`personal_clone` is an agentic system designed to act as a "second brain," remembering and accumulating your experiences, memories, and interaction details. It leverages Google Cloud Storage (GCS) for durable storage and Vertex AI Search (Discovery Engine) for powerful retrieval-augmented generation (RAG) capabilities.

## Core Functionality

The agent provides five primary functions to manage your knowledge base:

1.  **Remembering Experiences (`write_to_rag`)**:
    *   **Purpose**: To save a new experience into your knowledge base.
    *   **Usage**: Provide a `description`, the `content` of the experience, and an optional list of `tags`.
    *   **Output**: Returns the `file_path` of the newly created experience in GCS.

2.  **Recalling Information (`read_from_rag`)**:
    *   **Purpose**: To search your knowledge base for relevant information based on content. This function performs a semantic search using Vertex AI Search.
    *   **Usage**: Provide a clear `query`. You can also ask to filter by tags (though direct tag filtering is handled by the underlying Vertex AI Search configuration).
    *   **Output**: Returns a list of dictionaries. Each dictionary contains the `file_path` (relative path within the GCS bucket) of the source document and the `content` of the relevant experience. This `file_path` is crucial for subsequent update or delete operations.

3.  **Finding Experiences (`find_experiences`)**:
    *   **Purpose**: To locate experiences based on patterns in their filenames. This is useful when you know part of the filename or a specific naming convention.
    *   **Usage**: Provide a `pattern` (e.g., `experience_202507*.txt`) to match against file names in GCS.
    *   **Output**: Returns a list of dictionaries. Each dictionary provides detailed information about the matching experience, including its `file_path`, `description`, `tags`, and a `content_snippet` for easy identification.

4.  **Updating Information (`update_in_rag`)**:
    *   **Purpose**: To modify an existing experience.
    *   **Usage**: Requires the exact `file_path` of the experience (obtained from `read_from_rag` or `find_experiences`), the `new_content` to overwrite the old, and an optional list of `new_tags`.
    *   **Output**: A confirmation message upon successful update.

5.  **Forgetting Information (`delete_from_rag`)**:
    *   **Purpose**: To permanently remove an experience from your knowledge base.
    *   **Usage**: Requires the exact `file_path` of the experience (obtained from `read_from_rag` or `find_experiences`).
    *   **Output**: A confirmation message upon successful deletion.

## Technology Stack

*   **Agent Framework**: Google ADK (Agent Development Kit)
*   **Storage**: Google Cloud Storage (GCS) for storing raw experience files.
*   **Search & Retrieval**: Vertex AI Search (Discovery Engine) for indexing and semantic search capabilities.

### Indexing Latency

It's important to note that new data added to the Vertex AI Search datastore may take a few hours to be fully indexed and searchable. This is due to the asynchronous nature of the indexing process within Vertex AI Search.

## Important Notes on File Paths

The `file_path` is a critical identifier for `update_in_rag` and `delete_from_rag`.
*   `write_to_rag` generates and returns this `file_path`.
*   `read_from_rag` now returns the relative `file_path` (e.g., `user_preferences/porsche_color.txt`) for each relevant search result, allowing you to directly use it for management operations.
*   `find_experiences` also returns this relative `file_path` for experiences matching filename patterns.
