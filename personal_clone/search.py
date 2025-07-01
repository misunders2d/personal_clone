import os
import uuid
from datetime import datetime, timezone
from google.cloud import storage
from google.cloud import discoveryengine_v1
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# --- Configuration ---
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', '')
LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', '')
DATASTORE_ID = os.getenv('DATASTORE_ID', '')
BUCKET_NAME = os.getenv('BUCKET_NAME', '')
CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

try:
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
    storage_client = storage.Client(credentials=credentials)
    search_client = discoveryengine_v1.SearchServiceClient(credentials=credentials)
except FileNotFoundError:
    print(f"Error: Credentials file not found at '{CREDENTIALS_PATH}'.")
    print("Please ensure the GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly.")
    # Exit or handle gracefully
    exit()
except Exception as e:
    print(f"An unexpected error occurred during client initialization: {e}")
    exit()
# -------------------

def _generate_file_name():
    """Generates a standardized file name."""
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())
    return f"experience_{date_str}_{unique_id}.txt"

def _create_content_with_metadata(description: str, content: str, tags: list[str]) -> str:
    """Adds metadata to the content."""
    now_iso = datetime.now(timezone.utc).isoformat()
    tags_str = ", ".join(tags) if tags else ""
    metadata = f"""---
created: {now_iso}
modified: {now_iso}
description: {description}
tags: [{tags_str}]
---
"""
    return metadata + content

def write_to_rag(description: str, content: str, tags: list[str] = []) -> str:
    """
    Creates a new experience with a standardized file name and metadata.

    Args:
        description: A brief description of the experience.
        content: The main text of the experience.
        tags: An optional list of tags to categorize the experience.

    Returns:
        The file path of the newly created experience.
    """
    file_path = _generate_file_name()
    full_content = _create_content_with_metadata(description, content, tags)
    
    print(f"Attempting to upload '{file_path}' to bucket '{BUCKET_NAME}'...")
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)
        blob.upload_from_string(full_content)
        print(f"Successfully uploaded '{file_path}' to '{BUCKET_NAME}'.")
        return file_path
    except Exception as e:
        return f"An unexpected error occurred during upload: {e}"

def update_in_rag(file_path: str, new_content: str, new_tags: list[str] = []) -> str:
    """
    Updates an existing experience, preserving original creation date and updating the modified date and tags.

    Args:
        file_path: The file path of the experience to update.
        new_content: The new content to overwrite the old content.
        new_tags: An optional new list of tags to overwrite the old ones.

    Returns:
        A confirmation message.
    """
    print(f"Attempting to update '{file_path}' in bucket '{BUCKET_NAME}'...")
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)

        # Get original metadata
        original_content = blob.download_as_string().decode('utf-8')
        metadata_part = original_content.split('---')[1]
        created_date = metadata_part.split('created: ')[1].split('\n')[0]
        description = metadata_part.split('description: ')[1].split('\n')[0]
        
        # Use new tags if provided, otherwise keep the old ones
        if new_tags: # Check if new_tags is not empty
            tags_str = ", ".join(new_tags)
        else:
            # Extract existing tags from metadata_part
            tags_line = next((line for line in metadata_part.splitlines() if line.strip().startswith('tags:')), None)
            if tags_line:
                # Extract content within brackets, then split by comma and strip spaces
                tags_str = tags_line.split('[')[1].split(']')[0].strip()
            else:
                tags_str = ""

        now_iso = datetime.now(timezone.utc).isoformat()
        metadata = f"""---
created: {created_date}
modified: {now_iso}
description: {description}
tags: [{tags_str}]
---
"""
        full_content = metadata + new_content
        
        blob.upload_from_string(full_content)
        print(f"Successfully updated '{file_path}' in '{BUCKET_NAME}'.")
        return f"Successfully updated {file_path}."
    except Exception as e:
        return f"An unexpected error occurred during update: {e}"

def delete_from_rag(file_path: str) -> str:
    """
    Deletes an experience from the GCS bucket.

    Args:
        file_path: The file path of the experience to delete.

    Returns:
        A confirmation message.
    """
    print(f"Attempting to delete '{file_path}' from bucket '{BUCKET_NAME}'...")
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)
        blob.delete()
        print(f"Successfully deleted '{file_path}' from '{BUCKET_NAME}'.")
        return f"Successfully deleted {file_path}."
    except Exception as e:
        return f"An unexpected error occurred during deletion: {e}"

def find_experiences(pattern: str) -> list[dict]:
    """
    Finds experiences in the GCS bucket matching a pattern and returns detailed information.

    Args:
        pattern: A glob-style pattern to match against file names (e.g., "experience_202507*").

    Returns:
        A list of dictionaries, each containing 'file_path', 'description', 'tags', and 'content_snippet'.
    """
    print(f"Searching for files matching '{pattern}' in bucket '{BUCKET_NAME}'...")
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = storage_client.list_blobs(BUCKET_NAME, match_glob=pattern)
        
        results = []
        for blob in blobs:
            try:
                content = blob.download_as_string().decode('utf-8')
                parts = content.split('---', 2) # Split into metadata, content, and potential remaining parts
                
                description = "N/A"
                tags = []
                content_snippet = ""

                if len(parts) > 1:
                    metadata_part = parts[1]
                    # Extract description
                    desc_match = [line for line in metadata_part.splitlines() if line.strip().startswith('description:')]
                    if desc_match:
                        description = desc_match[0].split(':', 1)[1].strip()

                    # Extract tags
                    tags_match = [line for line in metadata_part.splitlines() if line.strip().startswith('tags:')]
                    if tags_match:
                        tags_str = tags_match[0].split('[', 1)[1].split(']', 1)[0].strip()
                        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                
                if len(parts) > 2:
                    content_body = parts[2].strip()
                    content_snippet = content_body[:200] + "..." if len(content_body) > 200 else content_body

                results.append({
                    "file_path": blob.name,
                    "description": description,
                    "tags": tags,
                    "content_snippet": content_snippet
                })
            except Exception as e:
                print(f"Error processing blob {blob.name}: {e}")
                # Optionally, add a partial result or skip
                results.append({
                    "file_path": blob.name,
                    "description": "Error reading content",
                    "tags": [],
                    "content_snippet": f"Error: {e}"
                })
        return results
    except Exception as e:
        return [{"error": f"An unexpected error occurred during search: {e}"}]

def read_from_rag(query: str) -> list[dict]:
    """
    Performs a search query against the Vertex AI Search datastore and returns detailed results.

    Args:
        query: The search query (e.g., "What was the key point about project X?").

    Returns:
        A list of dictionaries, each containing 'file_path' and 'content'.
    """
    print(f"Querying datastore '{DATASTORE_ID}' with: '{query}'...")
    try:
        serving_config = search_client.serving_config_path(
            project=PROJECT_ID,
            location=LOCATION,
            data_store=DATASTORE_ID,
            serving_config="default_config",
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=5,
        )

        response = search_client.search(request)
        
        results = []
        for i, result in enumerate(response.results):
            file_path = result.document.derived_struct_data['link'].replace(f"gs://{BUCKET_NAME}/", "") if 'link' in result.document.derived_struct_data else "N/A"
            if 'extractive_answers' in result.document.derived_struct_data:
                extractive_answers = result.document.derived_struct_data['extractive_answers']
                if extractive_answers and len(extractive_answers) > 0:
                    content = extractive_answers[0]['content']
                else:
                    content = "No extractive answers found."
            else:
                content = result.document.content if result.document.content else "No content found."
            
            results.append({
                "file_path": file_path,
                "content": content
            })

        if not results:
            return [{"file_path": "N/A", "content": "No relevant results found in the datastore."}]

        return results

    except Exception as e:
        return [{"file_path": "N/A", "content": f"Error: Could not query the datastore. Details: {e}"}]
