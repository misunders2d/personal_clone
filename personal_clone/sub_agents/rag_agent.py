import os, re
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools import AgentTool

from ..utils.gdrive_utils import (
    upload_file_to_drive,
    download_file_from_drive,
    update_file_in_drive,
    delete_file_from_drive,
    list_files_in_folder,
    get_or_create_folder,
)
from ..utils.pinecone_utils import (
    generate_embedding,
    upsert_vectors,
    query_vectors,
    delete_vectors,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

# --- Configuration ---

# -------------------


def _generate_file_name():
    """Generates a standardized file name."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    unique_id = str(uuid.uuid4())
    return f"experience_{date_str}_{unique_id}.txt"


def _create_content_with_metadata(
    description: str,
    content: str,
    tags: list[str],
    access_type: Optional[str] = None,
    clickup_task_id: Optional[str] = None,
) -> str:
    """Adds metadata to the content."""
    now_iso = datetime.now(timezone.utc).isoformat()
    tags_str = ", ".join(tags) if tags else ""

    # Handle default access_type inside the function
    effective_access_type = access_type if access_type is not None else "private"
    clickup_task_id_str = f"""
clickup_task_id: {clickup_task_id}" if clickup_task_id else """

    metadata = f"""---
created: {now_iso}
modified: {now_iso}
description: {description}
tags: [{tags_str}]
access_type: {effective_access_type}{clickup_task_id_str}
---
"""
    return metadata + content


def write_to_rag(
    description: str,
    content: str,
    tags: list[str] = [],
    access_type: Optional[str] = None,
    folder_id: Optional[str] = None,
    clickup_task_id: Optional[str] = None,
) -> str:
    """
    Creates a new experience with a standardized file name and metadata.

    Args:
        description: A brief description of the experience.
        content: The main text of the experience.
        tags: An optional list of tags to categorize the experience.
        access_type: 'private' or 'public' to control access. If None, defaults to 'private'.
        folder_id: The ID of the Google Drive folder. If None, it defaults to 'experiences' folder in My Drive.
        clickup_task_id: Optional ClickUp task ID to link.

    Returns:
        The file ID of the newly created experience in Google Drive.
    """
    if folder_id is None:
        folder_id = get_or_create_folder("experiences", "root")

    # Handle default access_type inside the function
    effective_access_type = access_type if access_type is not None else "private"

    file_name = _generate_file_name()
    full_content = _create_content_with_metadata(
        description, content, tags, effective_access_type, clickup_task_id
    )

    print(f"Attempting to upload '{file_name}' to Google Drive...")
    try:
        file_id = upload_file_to_drive(file_name, full_content, folder_id)
        print(
            f"Successfully uploaded '{file_name}' to Google Drive with ID: {file_id}."
        )

        # Generate embedding and upsert to Pinecone
        embedding = generate_embedding(content)
        metadata = {
            "file_name": file_name,
            "description": description,
            "tags": tags,
            "access_type": effective_access_type,
        }
        if clickup_task_id:
            metadata["clickup_task_id"] = clickup_task_id
        upsert_vectors(vectors=[(file_id, embedding, metadata)])
        print(f"Successfully upserted embedding for '{file_name}' to Pinecone.")

        return file_id
    except Exception as e:
        return f"An unexpected error occurred during write: {e}"


def update_in_rag(
    file_id: str,
    new_content: str,
    new_tags: list[str] = [],
    new_access_type: Optional[str] = None,
    folder_id: Optional[str] = None,
    clickup_task_id: Optional[str] = None,
) -> str:
    """
    Updates an existing experience, preserving original creation date and updating the modified date and tags.

    Args:
        file_id: The file ID of the experience to update in Google Drive.
        new_content: The new content to overwrite the old content.
        new_tags: An optional new list of tags to overwrite the old ones.
        new_access_type: An optional new access type ('private' or 'public') to overwrite the old one. If None, keeps the old access type.
        folder_id: The ID of the Google Drive folder. If None, it defaults to 'experiences' folder in My Drive.
        clickup_task_id: Optional ClickUp task ID to link.

    Returns:
        A confirmation message.
    """
    if folder_id is None:
        folder_id = get_or_create_folder("experiences", "root")

    print(f"Attempting to update '{file_id}' in Google Drive...")
    try:
        original_full_content = download_file_from_drive(file_id)
        parts = original_full_content.split("---", 2)

        if len(parts) < 2:
            raise ValueError("Invalid content format: metadata not found.")

        metadata_part = parts[1]

        # Extract original metadata
        created_date = next(
            (
                line.split(":", 1)[1].strip()
                for line in metadata_part.splitlines()
                if line.strip().startswith("created:")
            ),
            "",
        )
        description = next(
            (
                line.split(":", 1)[1].strip()
                for line in metadata_part.splitlines()
                if line.strip().startswith("description:")
            ),
            "",
        )

        # Determine tags
        if new_tags:
            tags_str = ", ".join(new_tags)
        else:
            tags_line = next(
                (
                    line
                    for line in metadata_part.splitlines()
                    if line.strip().startswith("tags:")
                ),
                None,
            )
            if tags_line:
                match = re.search(r"\[(.*?)\]", tags_line)
                if match:
                    tags_content = match.group(1).strip()
                    tags_str = tags_content
                else:
                    tags_str = ""
            else:
                tags_str = ""

        # Determine access_type
        if new_access_type is not None:
            access_type = new_access_type
        else:
            access_type_line = next(
                (
                    line
                    for line in metadata_part.splitlines()
                    if line.strip().startswith("access_type:")
                ),
                None,
            )
            if access_type_line:
                access_type = access_type_line.split(":", 1)[1].strip()
            else:
                access_type = "private"  # Default if not found

        # Extract or update clickup_task_id
        if clickup_task_id is None:
            clickup_task_id = next(
                (
                    line.split(":", 1)[1].strip()
                    for line in metadata_part.splitlines()
                    if line.strip().startswith("clickup_task_id:")
                ),
                None,
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        clickup_task_id_str = f"""
clickup_task_id: {clickup_task_id}" if clickup_task_id else """
        metadata = f"""---
created: {created_date}
modified: {now_iso}
description: {description}
tags: [{tags_str}]
access_type: {access_type}{clickup_task_id_str}
---
"""
        full_content = metadata + new_content

        update_file_in_drive(file_id, full_content)
        print(f"Successfully updated '{file_id}' in Google Drive.")

        # Update embedding in Pinecone
        embedding = generate_embedding(new_content)
        pinecone_metadata = {
            "file_name": file_id,  # Using file_id as file_name for Pinecone metadata consistency
            "description": description,
            "tags": [tag.strip() for tag in tags_str.split(",") if tag.strip()],
            "access_type": access_type,
        }
        if clickup_task_id:
            pinecone_metadata["clickup_task_id"] = clickup_task_id
        upsert_vectors(vectors=[(file_id, embedding, pinecone_metadata)])
        print(f"Successfully updated embedding for '{file_id}' in Pinecone.")

        return f"Successfully updated {file_id}."
    except Exception as e:
        return f"An unexpected error occurred during update: {e}"


def delete_from_rag(file_id: str, folder_id: Optional[str] = None) -> str:
    """
    Deletes an experience from Google Drive and its corresponding vector from Pinecone.

    Args:
        file_id: The file ID of the experience to delete.
        folder_id: The ID of the Google Drive folder. If None, it defaults to 'experiences' folder in My Drive.

    Returns:
        A confirmation message.
    """
    if folder_id is None:
        folder_id = get_or_create_folder("experiences", "root")

    print(f"Attempting to delete '{file_id}' from Google Drive...")
    try:
        delete_file_from_drive(file_id)
        print(f"Successfully deleted '{file_id}' from Google Drive.")

        # Delete vector from Pinecone
        delete_vectors(ids=[file_id])
        print(f"Successfully deleted vector for '{file_id}' from Pinecone.")

        return f"Successfully deleted {file_id}."
    except Exception as e:
        return f"An unexpected error occurred during deletion: {e}"


def find_experiences(pattern: str, folder_id: Optional[str] = None) -> list[dict]:
    """
    Finds experiences in the Google Drive folder matching a pattern and returns detailed information.

    Args:
        pattern: A regex pattern to match against file names (e.g., "experience_202507.*txt").
        folder_id: The ID of the Google Drive folder. If None, it defaults to 'experiences' folder in My Drive.

    Returns:
        A list of dictionaries, each containing 'file_id', 'file_name', 'description', 'tags', 'access_type', and 'content_snippet'.
    """
    if folder_id is None:
        folder_id = get_or_create_folder("experiences", "root")

    print(f"Searching for files matching '{pattern}' in Google Drive...")
    try:
        items = list_files_in_folder(folder_id)

        results = []
        for item in items:
            file_id = item["id"]
            file_name = item["name"]

            if re.match(pattern, file_name):
                try:
                    content = download_file_from_drive(file_id)
                    parts = content.split("---", 2)

                    description = "N/A"
                    tags = []
                    access_type = "private"
                    content_snippet = ""

                    if len(parts) > 1:
                        metadata_part = parts[1]
                        # Extract description
                        desc_match = [
                            line
                            for line in metadata_part.splitlines()
                            if line.strip().startswith("description:")
                        ]
                        if desc_match:
                            description = desc_match[0].split(":", 1)[1].strip()

                        # Extract tags
                        tags_match = [
                            line
                            for line in metadata_part.splitlines()
                            if line.strip().startswith("tags:")
                        ]
                        if tags_match:
                            tags_str = (
                                tags_match[0].split("[", 1)[1].split("]", 1)[0].strip()
                            )
                            tags = [
                                tag.strip()
                                for tag in tags_str.split(",")
                                if tag.strip()
                            ]

                        # Extract access_type
                        access_type_match = [
                            line
                            for line in metadata_part.splitlines()
                            if line.strip().startswith("access_type:")
                        ]
                        if access_type_match:
                            access_type = access_type_match[0].split(":", 1)[1].strip()

                    if len(parts) > 2:
                        content_body = parts[2].strip()
                        content_snippet = (
                            content_body[:200] + "..."
                            if len(content_body) > 200
                            else content_body
                        )

                    results.append(
                        {
                            "file_id": file_id,
                            "file_name": file_name,
                            "description": description,
                            "tags": tags,
                            "access_type": access_type,
                            "content_snippet": content_snippet,
                        }
                    )
                except Exception as e:
                    print(f"Error processing file {file_name} (ID: {file_id}): {e}")
                    results.append(
                        {
                            "file_id": file_id,
                            "file_name": file_name,
                            "description": "Error reading content",
                            "tags": [],
                            "access_type": "N/A",
                            "content_snippet": f"Error: {e}",
                        }
                    )
        return results
    except Exception as e:
        return [{"error": f"An unexpected error occurred during search: {e}"}]


def read_from_rag(
    query: str,
    top_k: int = 5,
    access_type: Optional[str] = None,
    folder_id: Optional[str] = None,
) -> list[dict]:
    """
    Performs a search query against the Pinecone index and returns detailed results from Google Drive.

    Args:
        query: The search query (e.g., "What was the key point about project X?").
        top_k: The number of top results to retrieve from Pinecone.
        access_type: Filter by 'private' or 'public' experiences.
        folder_id: The ID of the Google Drive folder. If None, it defaults to 'experiences' folder in My Drive.

    Returns:
        A list of dictionaries, each containing 'file_id', 'file_name', 'content', 'description', 'tags', and 'access_type'.
    """
    if folder_id is None:
        folder_id = get_or_create_folder("experiences", "root")

    print(f"Querying Pinecone with: '{query}'...")
    try:
        query_embedding = generate_embedding(query)

        # Build filter for Pinecone query
        pinecone_filter = {}
        if access_type:
            pinecone_filter["access_type"] = access_type

        query_results = query_vectors(
            query_embedding, top_k=top_k, include_metadata=True, filters=pinecone_filter
        )

        results = []
        for match in query_results:
            file_id = match["id"]
            metadata = match["metadata"]

            try:
                full_content = download_file_from_drive(file_id)
                parts = full_content.split("---", 2)
                content_body = parts[2].strip() if len(parts) > 2 else ""

                results.append(
                    {
                        "file_id": file_id,
                        "file_name": metadata.get("file_name", "N/A"),
                        "content": content_body,
                        "description": metadata.get("description", "N/A"),
                        "tags": metadata.get("tags", []),
                        "access_type": metadata.get("access_type", "private"),
                    }
                )
            except Exception as e:
                print(f"Error downloading content for file ID {file_id}: {e}")
                results.append(
                    {
                        "file_id": file_id,
                        "file_name": metadata.get("file_name", "N/A"),
                        "content": f"Error: Could not retrieve content. {e}",
                        "description": metadata.get("description", "N/A"),
                        "tags": metadata.get("tags", []),
                        "access_type": metadata.get("access_type", "private"),
                    }
                )

        if not results:
            return [
                {"file_id": "N/A", "content": "No relevant results found in Pinecone."}
            ]

        return results

    except Exception as e:
        return [
            {
                "file_id": "N/A",
                "content": f"Error: Could not query Pinecone. Details: {e}",
            }
        ]


def create_rag_agent_tool(name="rag_agent"):
    rag_agent = Agent(
        name=name,
        description="An agent that manages experiences and memories in the RAG system (Google Drive + Pinecone)",
        instruction="You are a RAG agent. Use the provided tools to manage user experiences, including memorizing things and recalling past experiences.",
        model=os.environ["MODEL_NAME"],
        tools=[
            write_to_rag,
            read_from_rag,
            update_in_rag,
            delete_from_rag,
            find_experiences,
        ],
    )
    return AgentTool(agent=rag_agent, skip_summarization=True)
