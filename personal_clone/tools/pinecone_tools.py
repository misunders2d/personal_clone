from pinecone import Pinecone, SearchQuery
import uuid
from datetime import datetime

from google.adk.tools.tool_context import ToolContext
from google.adk.tools.function_tool import FunctionTool

from .. import config

pc = Pinecone(api_key=config.PINECONE_API_KEY)
index_name = config.PINECONE_INDEX_NAME


def list_indexes() -> dict:
    """
    Lists all available indexes in Pinecone

    Returns:
        dict: The result of the list_indexes operation.

    """
    try:
        index_names = pc.list_indexes().names()
        return {"status": "success", "index_names": index_names}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def create_memory(
    tool_context: ToolContext,
    namespace: str,
    text: str,
    short_description: str,
    category: str,
    tags: list[str],
    related_people: list[str] = [],
    related_memories: list[dict] = [],
) -> dict:
    """
    Creates a record in a specific Pinecone index.

    Args:
        tool_context (ToolContext): a ToolContext object.
        namespace (str): Required. The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience).
        text (str): Required. the main content/body of the memory.
        short_description (str): Required. short summary/title for the memory.
        category (str): Required. one of the allowed categories (e.g., "project", "memory", "strategy", "note", "task", "professional").
        tags (list[str]): Required. list of keyword tags.
        related_people (list[str]): Optional. list of person ids (e.g., "per_2025_09_05_8909994f") referenced by this memory.
        related_memories (list[dict]): Optional. references to other memories:
            [{"related_memory_id": "mem_...", "relation_type": "related_to"}]

    Returns:
        dict: The result of the upsert operation.

    Example:
        records = [
            {
                "memory_id": None,
                "short_description": "Call with Bernard about promotion",
                "text": "Bernard suggested I consider a raise and work toward Sales Director. Discuss with Igor and Margarita.",
                "category": "strategy",
                "tags": ["career", "raise"],
                "related_people": ["per_2025_09_16_c08e0ed4", "per_2025_10_02_41c37001"],
                "related_memories": None,
            }
        ]
    """
    try:

        missing = []
        if not namespace:
            missing.append("namespace")
        if not text:
            missing.append("text")
        if not short_description:
            missing.append("short_description")
        if not category:
            missing.append("category")
        if tags is None:
            missing.append("tags")
        if missing:
            return {
                "status": "failed",
                "missing": missing,
                "error": f"Missing required parameters: {', '.join(missing)}",
            }

        related_people = related_people or []
        related_memories = related_memories or []

        index = pc.Index(index_name)

        date_value = datetime.now().strftime("%Y_%m_%d")
        memory_id = f"mem_{date_value}_{uuid.uuid4().hex}"

        # actual memory creation or update
        single_record = {
            "id": memory_id,
            "text": text,
            "short_description": short_description,
            "category": category,
            "tags": tags,
        }
        if related_people:
            single_record["related_people"] = related_people  # type: ignore
        if related_memories:
            single_record["related_memories"] = related_memories  # type: ignore
        
        tool_confirmation = tool_context.tool_confirmation
        if tool_confirmation:
            print(f"[CONFIRMING]{tool_confirmation.confirmed}", end = "\n\n\n")

        records = [single_record]
        _ = index.upsert_records(namespace=namespace, records=records)

        # verifying that memory was updated/created
        check = index.fetch(ids=[x["id"] for x in records], namespace=namespace)
        if check and check.vectors:
            return {
                "status": "success",
                "response": f"id {records[0].get('id')} successfully updated in {namespace} namespace",
            }
        else:
            return {
                "status": "failed",
                "response": f"id {records[0].get('id')} not inserted to {namespace}",
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def update_memory(
    tool_context: ToolContext, namespace: str, memory_id: str, updates: dict = {}
) -> dict:
    """
    Modifies/updates a specific record in a specific Pinecone index.

    Args:
        tool_context (ToolContext): a ToolContext object.
        namespace (str): Required. The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience).
        memory_id (str): Required. memory_id string. Use None or omit for new records (function will generate a UUID).
        updates: (dict): Required. a dict of updates applied to the specific memory. MUST CONTAIN AT LEAST ONE OF THE FOLLOWING:
            - text (str): the main content/body of the memory to update.
            - short_description (str): short summary/title for the memory to update.
            - category (str): one of the allowed categories (e.g., "project", "memory", "strategy", "note", "task", "professional") to update.
            - tags (list[str]): list of keyword tags to update.
            - related_people (Optional [list[str]]): list of person ids (e.g., "per_2025_09_05_8909994f") referenced by this memory to update.
            - related_memories (Optional [list[dict]]) to update: references to other memories:
                [{"related_memory_id": "mem_...", "relation_type": "related_to"}]

    Returns:
        dict: The result of the upsert operation.

    Example (update):
        records = [
            {
                "short_description": "Call with Bernard about promotion (updated)",
                "text": "Updated notes: Bernard suggested a raise...",
                "tags": ["career", "raise", "promotion"]
            }
        ]

    """
    allowed_fields = (
        "text",
        "short_description",
        "category",
        "tags",
        "related_people",
        "related_memories",
    )
    if not isinstance(updates, dict) or not updates:
        return {
            "status": "error",
            "message": f"`updates` must be a dict with at least one of the allowed values: {allowed_fields}",
        }
    if any(key not in allowed_fields for key in updates.keys()):
        return {"status": "error", "message": "forbidden keys in the `updates` dict"}

    try:
        index = pc.Index(index_name)

        # Get the user's confirmation decision from the tool_context
        tool_confirmation = tool_context.tool_confirmation

        # If a confirmation decision has not been made, request one from the user.
        if not tool_confirmation:
            memory_to_update = index.fetch(ids=[memory_id], namespace=namespace)
            if not memory_to_update.vectors:
                return {
                    "status": "error",
                    "message": f"Memory {memory_id} not found in namespace {namespace}",
                }

            mem_data = memory_to_update.vectors[memory_id].to_dict()

            # This will pause the tool's execution and prompt the user for confirmation.
            # The tool will be executed again with the user's decision.
            tool_context.request_confirmation(
                hint=f"You are about to update memory '{memory_id}'. Current content: {mem_data.get('metadata')}. Do you approve?",
                payload={"confirmed": False},
            )
            # Return a pending status to indicate that the tool is waiting for user input.
            return {"status": "pending", "message": "Waiting for user confirmation."}

        # If a confirmation decision has been made, check the payload.
        if not tool_confirmation.confirmed:
            return {
                "status": "cancelled",
                "message": "User cancelled the memory update.",
            }

        confirmed = tool_confirmation.confirmed

        print(f"[CONFIRMED]: {confirmed}", end = "\n\n\n")
        print(f"[TOOL CONFIRMATION]: {tool_confirmation}", end = "\n\n\n")
        print(f"[TOOL CONTEXT]: {tool_context}", end = "\n\n\n")

        if confirmed:
            # --- User has approved, so proceed with the update ---
            records = {key: value for key, value in updates.items()}
            _ = index.update(id=memory_id, namespace=namespace, set_metadata=records)

            # Verifying that memory was updated/created
            check = index.fetch(ids=[x["id"] for x in records], namespace=namespace)
            if check and check.vectors:
                return {
                    "status": "success",
                    "response": f"id {records[0].get('id')} successfully updated in {namespace} namespace",
                }
            else:
                return {
                    "status": "failed",
                    "response": f"id {records[0].get('id')} not inserted to {namespace}",
                }
        else:
            tool_context.actions.escalate
            return {
                "status": "cancelled",
                "message": "User cancelled the memory update.",
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def delete_memory(namespace: str, memory_id: str):
    """
    Deletes a specific record from  a specific Pinecone index.

    Args:
        namespace (str): The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience)..
        memory_id (str): An ID of the record to delete.

    Returns:
        dict: The result of the delete operation.
    """
    try:
        index = pc.Index(index_name)
        _ = index.delete(ids=[memory_id], namespace=namespace)
        check = index.fetch([memory_id], namespace=namespace)
        if check and check.vectors:
            return {
                "status": "failed",
                "message": f"record {memory_id} still exists in {namespace}",
            }
        return {
            "status": "success",
            "message": f"record {memory_id} successfully deleted from {namespace}",
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def search_records(namespace: str, search_query: str):
    """
    Searches for memories/records in Pinecone

    Args:
        namespace (str): The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience)..
        search_query (str): The search query to search in Pinecone records

    Returns:
        dict: The result of the search operation along with additional metadata (if any).

    """
    try:
        query = SearchQuery(inputs={"text": search_query}, top_k=20)

        index = pc.Index(index_name)
        results = index.search(namespace=namespace, query=query)
        if results:
            summary = results.get("result", {}).get("hits")
            return {"status": "success", "search_results": summary}
        return {"status": "failed", "search_results": results}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def create_pinecone_toolset():
    # pinecone_toolset = MCPToolset(
    #     connection_params=StdioConnectionParams(
    #         server_params=StdioServerParameters(
    #             command="npx",
    #             args=[
    #                 "-y",
    #                 "@pinecone-database/mcp",
    #             ],
    #             env={"PINECONE_API_KEY": config.PINECONE_API_KEY},
    #         ),
    #     ),
    # )

    return [
        FunctionTool(create_memory, require_confirmation=True),
        update_memory,
    ]  # , search_records, delete_record]
