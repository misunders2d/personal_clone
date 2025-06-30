import os
from google.cloud import storage
from google.cloud import discoveryengine_v1
from google.oauth2 import service_account
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# --- Configuration ---
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', '')
LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', '')  # Use "global" for the API endpoint
DATASTORE_ID = os.getenv('DATASTORE_ID', '')
BUCKET_NAME = os.getenv('BUCKET_NAME', '')
credentials = service_account.Credentials.from_service_account_file('personal_clone/.secrets/personal-clone-464511-3672028375bb.json')
# -------------------

def write_to_rag(file_path: str, content: str):
    """
    Uploads a text file to the GCS bucket, which triggers ingestion
    into the Vertex AI Search datastore.

    Args:
        file_path: The name of the file to create in the bucket (e.g., "conversation_123.txt").
        content: The text content to write into the file.
    """
    print(f"Attempting to upload '{file_path}' to bucket '{BUCKET_NAME}'...")
    try:
        storage_client = storage.Client(credentials=credentials)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)

        blob.upload_from_string(content)
        print(f"Successfully uploaded '{file_path}' to '{BUCKET_NAME}'.")
        print("Vertex AI Search will now automatically index this file.")
    except Exception as e:
        print(f"An error occurred during upload: {e}")


def read_from_rag(query: str) -> str:
    """
    Performs a search query against the Vertex AI Search datastore.

    Args:
        query: The search query (e.g., "What was the key point about project X?").

    Returns:
        A string containing the search results.
    """
    print(f"Querying datastore '{DATASTORE_ID}' with: '{query}'...")
    try:
        client = discoveryengine_v1.SearchServiceClient(credentials=credentials)

        # The full resource name of the serving config
        serving_config = client.serving_config_path(
            project=PROJECT_ID,
            location=LOCATION,
            data_store=DATASTORE_ID,
            serving_config="default_config",
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=5,  # How many results to retrieve
        )

        response = client.search(request)
        
        results = []
        for i, result in enumerate(response.results):
            # Assuming the data is unstructured text, the content is in the 'content' field
            # of the 'document.derived_struct_data'
            if 'extractive_answers' in result.document.derived_struct_data:
                extractive_answers = result.document.derived_struct_data['extractive_answers']
                if extractive_answers and len(extractive_answers) > 0:
                    content = extractive_answers[0]['content']
                else:
                    content = "No extractive answers found."
            else:
                content = "No extractive answers found."
            results.append(f"Result {i+1}:\n{content}\n")

        if not results:
            return "No relevant results found in the datastore."

        return "\n".join(results)

    except Exception as e:
        print(f"An error occurred during search: {e}")
        return f"Error: Could not query the datastore. Details: {e}"


if __name__ == '__main__':
    # --- Example Usage ---

    # 1. Write a new "experience" to the RAG store
    # This creates a file in your GCS bucket.
    # Vertex AI Search will automatically detect and index it.
    # Note: Indexing can take a few minutes.
    experience_to_add = "The user confirmed that billing is enabled for the 'personal-clone' project. The root cause of the gcloud error was likely a temporary authentication glitch or a propagation delay after a change was made."
    file_name = "experience_2025_06_30_01.txt"
    # write_to_rag(file_name, experience_to_add)

    print("\n" + "="*50 + "\n")

    # 2. Read from the RAG store
    # It might take a few minutes for the new file to be indexed.
    # If you run this immediately, the new experience might not appear.
    search_query = "what was the problem with the gcloud command"
    search_query = "what color of cars does user like?"
    search_results = read_from_rag(search_query)

    print("\n--- Search Results ---")
    print(search_results)
    print("--------------------")