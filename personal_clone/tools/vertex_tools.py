import os
import time

from google import genai
from google.genai import types

from .. import config

client = genai.Client(api_key=config.GEMINI_API_KEY, vertexai=False)


def create_file_search_store(display_name: str):
    # Create the file search store with an optional display name
    config = types.CreateFileSearchStoreConfigDict(display_name=display_name)
    file_search_store = client.file_search_stores.create(config=config)
    return file_search_store


def get_file_search_store(store_name: str):

    file_search_store_list = client.file_search_stores.list()
    for store in file_search_store_list:
        if store.display_name == store_name:
            return store
    return None


def upload_file_to_store(
    file_path: str, unique_file_name: str, store_name: str = "rag_documents"
):
    # Upload and import a file into the file search store, supply a unique file name which will be visible in citations
    try:
        file_search_store = get_file_search_store(store_name)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    if not file_search_store:
        return {
            "status": "error",
            "message": f"File search store `{store_name}` not found.",
        }
    if file_search_store.name:
        try:
            operation = client.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=file_search_store.name,
                config={
                    "display_name": unique_file_name,
                },
            )
            # Wait until import is complete
            while not operation.done:
                time.sleep(5)
                operation = client.operations.get(operation)
            return {
                "status": "success",
                "message": f"File {unique_file_name} uploaded successfully.",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"File ({file_path}) could not be uploaded: {e}.",
            }
    return {
        "status": "error",
        "message": f"File search store name ({store_name}) not found.",
    }


def bulk_upload_files(path_to_files: str, store_name: str) -> dict:
    allowed_extensions = (".txt", "pdf", ".docx")
    file_list_raw = os.listdir(path_to_files)
    file_list_clean = [
        x for x in file_list_raw if any(x.endswith(ext) for ext in allowed_extensions)
    ]
    successful_files = {}
    failed_files = {}
    for file in file_list_clean:
        result = upload_file_to_store(
            file_path=os.path.join(path_to_files, file),
            unique_file_name=file,
            store_name=store_name,
        )
        if result.get("status", "error") == "success":
            successful_files[file] = result.get("message")
        else:
            failed_files[file] = result.get("message")
    return {
        "results": {"successful_files": successful_files, "failed_files": failed_files}
    }


async def list_available_stores() -> list | dict:
    """
    Lists all available search file stores for the user.

    Args:
        None

    Returns:
        list: list of store names or dict with an error message
    """
    try:
        stores = client.file_search_stores.list()
        store_names = [x.display_name for x in stores]
        return store_names
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def list_documents_in_store(store_name: str):
    """
    Lists all available documents in a user's file search store.

    Args:
        store_name(str): the name of the store to list documents in. If you don't know the name - you can use `list_available_stores` to get the file store names.
    Returns:
        dict: success or error message, along with a list of documents and their respecitve names and update dates or error message.
    """
    try:
        file_search_store = get_file_search_store(store_name)
        if not (file_search_store and file_search_store.name):
            return {"status": "error", "message": "could not access file search store"}
        store_documents = []
        files_pager = client.file_search_stores.documents.list(
            parent=file_search_store.name
        )
        for file in files_pager:
            document_info = {
                "display_name": file.display_name,
                "update_time": file.update_time,
                # "name": file.name
            }
            store_documents.append(document_info)
        return {"status": "success", "files": store_documents}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def delete_file_search_store(display_name: str):
    file_search_store = get_file_search_store(display_name)
    if file_search_store and file_search_store.name:
        _ = client.file_search_stores.delete(
            name=file_search_store.name,
            config=types.DeleteFileSearchStoreConfig(force=True),
        )
    return None


async def search_file_store(query: str, store_name: str) -> dict:
    """
    Search the file search store (documents storage) for user query.

    Args:
        query(str): A query to search for
        store_name(str): the name of the store to list documents in

    Returns:
        dict: search results along with grounding data
    """
    try:
        file_search_store = get_file_search_store(store_name)
        if not file_search_store or not file_search_store.name:
            return {
                "status": "error",
                "message": f"File search store `{store_name}` not found.",
            }
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[file_search_store.name]
                        )
                    )
                ]
            ),
        )
        grounding_dict = {}
        if (
            response
            and response.candidates
            and response.candidates[0].grounding_metadata
        ):
            grounding_data = response.candidates[0].grounding_metadata.grounding_chunks
            if grounding_data:
                for chunk in grounding_data:
                    chunk_dict = chunk.to_json_dict().get("retrieved_context", {})
                    if isinstance(chunk_dict, dict):
                        title = chunk_dict.get("title")
                        text = chunk_dict.get("text")
                        if title not in grounding_dict:
                            grounding_dict[title] = [text]
                        else:
                            grounding_dict[title].append(text)
            return {"search_results": response.text, "grounding_data": grounding_dict}
        return {"search_results": "nothing found"}
    except Exception as e:
        return {"error": str(e)}
