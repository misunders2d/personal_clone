from pinecone import Pinecone, SearchQuery
import uuid
from datetime import datetime
import json

from google.adk.tools.tool_context import ToolContext

# from google.adk.tools.function_tool import FunctionTool

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

        user_id = tool_context.state.get("user_id", "unknown_user")

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

        if namespace == "people":
            return {
                "status": "error",
                "message": "You must use `create_people` function to create records of people",
            }

        if namespace not in ("personal", "professional"):
            return {
                "status": "error",
                "message": "Only `personal` or `professional` namespaces are allowed",
            }

        related_people = related_people or []
        related_memories = related_memories or []

        index = pc.Index(index_name)

        date_value = datetime.now()
        memory_id = f"mem_{date_value.strftime("%Y_%m_%d")}_{uuid.uuid4().hex}"

        # actual memory creation or update

        single_record = {
            "id": memory_id,
            "user_id": user_id,
            "created_at": int(date_value.timestamp()),
            "text": text,
            "short_description": short_description,
            "category": category,
            "tags": tags,
        }
        if related_people:
            single_record["related_people"] = related_people
        if related_memories:
            single_record["related_memories"] = related_memories

        tool_confirmation = tool_context.tool_confirmation
        if not tool_confirmation:
            print("[REQUESTING TOOL CONFIRMATION]", end="\n\n\n")
            tool_context.request_confirmation(
                hint="Please confirm the creation of new memory"
            )
            print(
                {"status": "pending", "message": "waiting for user confirmation"},
                end="\n\n\n",
            )
            return {"status": "pending", "message": "waiting for user confirmation"}

        # if tool_context.tool_confirmation and tool_context.tool_confirmation.confirmed:
        if True:

            print("[TOOL CONFIRMATION RECEIVED]", end="\n\n\n")

            records = [single_record]
            _ = index.upsert_records(namespace=namespace, records=records)

            # verifying that memory was updated/created
            check = index.fetch(ids=[x["id"] for x in records], namespace=namespace)
            if check and check.vectors:
                print(
                    {
                        "status": "success",
                        "response": f"id {records[0].get('id')} successfully updated in {namespace} namespace",
                    },
                    end="\n\n\n",
                )
                return {
                    "status": "success",
                    "response": f"id {records[0].get('id')} successfully updated in {namespace} namespace",
                }
            else:
                print(
                    {
                        "status": "failed",
                        "response": f"id {records[0].get('id')} not inserted to {namespace}",
                    },
                    end="\n\n\n",
                )
                return {
                    "status": "failed",
                    "response": f"id {records[0].get('id')} not inserted to {namespace}",
                }
        # else:
        #     print("[TOOL CONFIRMATION REJECTED]", end="\n\n\n")
        #     return {
        #         "status": "not confirmed",
        #         "message": "the function call was never confirmed by the user",
        #     }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def create_people(
    tool_context: ToolContext,
    first_name: str,
    last_name: str,
    role: str,
    user_ids: list[dict[str, str]],
    relations: list[dict[str, str]] = [],
) -> dict:
    """
    A dedicated function to create records about people, one person at a time.

    Args:
        - tool_context (ToolContext): a ToolContext object.
        - first_name (str): Required. Person's first name.
        - last_name (str): Required. Person's last name. Use an empty string ("") if last name is unknown, but it is highly recommended to find out the user's last name to avoid ambiguity.
        - role (str): Required. Short description of the role or how this person is perceived and related to the "owner" user. Example: 'friend', 'mentor', 'colleague'.
        - user_ids (list[dict[str, str]]): Required. Identifiers that can be used to recognize this person, with type labels. Example: [{'id_type':'personal email','id_value':'user@example.com'},{'id_type':'telegram handle','id_value':'@tg_user'}]..
        - relations (list[dict[str, str]]): Optional. Connections to other people in the table. Example: [{'related_person_id':'per_abc123','relation_type':'son'}]..

    Returns:
        dict: The result of the upsert operation.

    """
    try:
        namespace = "people"
        user_id = tool_context.state.get("user_id", "unknown_user")

        missing = []
        if not first_name:
            missing.append("first_name")
        if not last_name:
            missing.append("last_name")
        if not role:
            missing.append("role")
        if not user_ids:
            missing.append("user_ids")
        if missing:
            return {
                "status": "failed",
                "missing": missing,
                "error": f"Missing required parameters: {', '.join(missing)}",
            }

        index = pc.Index(index_name)

        date_value = datetime.now()
        person_id = f"per_{date_value.strftime("%Y_%m_%d")}_{uuid.uuid4().hex}"

        # actual memory creation or update
        user_ids_str = ", ".join([x["id_value"] for x in user_ids])
        single_record = {
            "id": person_id,
            "user_id": user_id,
            "created_at": int(date_value.timestamp()),
            "first_name": first_name,
            "last_name": last_name,
            "text": f"{first_name} {last_name}. IDs: {user_ids_str}".strip(),
            "role": role,
            "user_ids": user_ids,
        }
        if relations:
            single_record["relations"] = relations

        # tool_confirmation = tool_context.tool_confirmation
        # if not tool_confirmation:
        #     print("[REQUESTING TOOL CONFIRMATION]", end="\n\n\n")
        #     tool_context.request_confirmation(
        #         hint="Please confirm the creation of new memory"
        #     )
        #     print(
        #         {"status": "pending", "message": "waiting for user confirmation"},
        #         end="\n\n\n",
        #     )
        #     return {"status": "pending", "message": "waiting for user confirmation"}

        # if tool_context.tool_confirmation and tool_context.tool_confirmation.confirmed:
        if True:

            print("[TOOL CONFIRMATION RECEIVED]", end="\n\n\n")

            records = [single_record]
            _ = index.upsert_records(namespace=namespace, records=records)

            # verifying that memory was updated/created
            check = index.fetch(ids=[x["id"] for x in records], namespace=namespace)
            if check and check.vectors:
                print(
                    {
                        "status": "success",
                        "response": f"id {records[0].get('id')} successfully updated in {namespace} namespace",
                    },
                    end="\n\n\n",
                )
                return {
                    "status": "success",
                    "response": f"id {records[0].get('id')} successfully updated in {namespace} namespace",
                }
            else:
                print(
                    {
                        "status": "failed",
                        "response": f"id {records[0].get('id')} not inserted to {namespace}",
                    },
                    end="\n\n\n",
                )
                return {
                    "status": "failed",
                    "response": f"id {records[0].get('id')} not inserted to {namespace}",
                }
        # else:
        #     print("[TOOL CONFIRMATION REJECTED]", end="\n\n\n")
        #     return {
        #         "status": "not confirmed",
        #         "message": "the function call was never confirmed by the user",
        #     }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def update_memory(
    tool_context: ToolContext, namespace: str, memory_id: str, updates: dict = {}
) -> dict:
    """
    Modifies/updates a specific record in a specific Pinecone namespace.

    Args:
        tool_context (ToolContext): a ToolContext object.
        namespace (str): Required. The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience).
        memory_id (str): Required. memory_id string.
        updates: (dict): Required. a dict of updates applied to the specific memory. MUST CONTAIN AT LEAST ONE OF THE FOLLOWING:
            - text (str): the main content/body of the memory to update.
            - short_description (str): short summary/title for the memory to update.
            - category (str): one of the allowed categories (e.g., "project", "memory", "strategy", "note", "task", "professional") to update.
            - tags (list[str]): list of keyword tags to update.
            - user_id (str): A unique user_id of the user who created this memory. Can be changed within the existing list of user_ids of the same user.
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
        memory_to_update = index.fetch(ids=[memory_id], namespace=namespace)
        if not memory_to_update.vectors:
            return {
                "status": "error",
                "message": f"Memory {memory_id} not found in namespace {namespace}",
            }

        # Get the user's confirmation decision from the tool_context
        # tool_confirmation = tool_context.tool_confirmation

        # # If a confirmation decision has not been made, request one from the user.
        # if not tool_confirmation:

        #     mem_data = memory_to_update.vectors[memory_id].to_dict()

        #     # This will pause the tool's execution and prompt the user for confirmation.
        #     # The tool will be executed again with the user's decision.
        #     tool_context.request_confirmation(
        #         hint=f"You are about to update memory '{memory_id}'. Current content: {mem_data.get('metadata')}. Do you approve?",
        #         payload={"confirmed": False},
        #     )
        #     # Return a pending status to indicate that the tool is waiting for user input.
        #     return {"status": "pending", "message": "Waiting for user confirmation."}

        # # If a confirmation decision has been made, check the payload.
        # if not tool_confirmation.confirmed:
        #     return {
        #         "status": "cancelled",
        #         "message": "User cancelled the memory update.",
        #     }

        # confirmed = tool_confirmation.confirmed

        # print(f"[CONFIRMED]: {confirmed}", end="\n\n\n")
        # print(f"[TOOL CONFIRMATION]: {tool_confirmation}", end="\n\n\n")
        # print(f"[TOOL CONTEXT]: {tool_context}", end="\n\n\n")

        # if confirmed:
        if True:
            # --- User has approved, so proceed with the update ---
            records = {key: value for key, value in updates.items()}
            records["updated_at"] = int(datetime.now().timestamp())

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
        # else:
        #     tool_context.actions.escalate
        #     return {
        #         "status": "cancelled",
        #         "message": "User cancelled the memory update.",
        #     }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def update_people(
    tool_context: ToolContext, person_id: str, updates: dict = {}
) -> dict:
    """
    Modifies/updates a specific person in "people" Pinecone namespace.

    Args:
        tool_context (ToolContext): a ToolContext object.
        person_id (str): Required. `person_id` string of a specific person to modify.
        updates: (dict): Required. a dict of updates applied to the specific memory. MUST CONTAIN AT LEAST ONE OF THE FOLLOWING:
            - first_name (str): Person's first name.
            - last_name (str): Person's last name. Use an empty string ("") if last name is unknown, but it is highly recommended to find out the user's last name to avoid ambiguity.
            - role (str): Short description of the role or how this person is perceived and related to the "owner" user. Example: 'friend', 'mentor', 'colleague'.
            - user_ids (list[dict[str, str]]): Required. Identifiers that can be used to recognize this person, with type labels. Example: [{'id_type':'personal email','id_value':'user@example.com'},{'id_type':'telegram handle','id_value':'@tg_user'}]..
            - relations (list[dict[str, str]]): Optional. Connections to other people in the table. Example: [{'related_person_id':'per_abc123','relation_type':'son'}]..


    Returns:
        dict: The result of the upsert operation.

    Example (update):
        records = [
            {
                "relations": {'per_2025_10_12_elksjdf':'friend'},
                "user_ids": {"personal email":"user@homeserver.com"},
                "last_name": "Jovanovich"
            }
        ]

    """
    namespace = "people"
    allowed_fields = (
        "first_name",
        "last_name",
        "role",
        "user_ids",
        "relations",
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
        person_to_update = index.fetch(ids=[person_id], namespace=namespace)
        if not person_to_update.vectors:
            return {
                "status": "error",
                "message": f"Person {person_to_update} not found in namespace {namespace}",
            }

        # Get the user's confirmation decision from the tool_context
        # tool_confirmation = tool_context.tool_confirmation

        # # If a confirmation decision has not been made, request one from the user.
        # if not tool_confirmation:

        #     person_data = person_to_update.vectors[person_id].to_dict()

        #     # This will pause the tool's execution and prompt the user for confirmation.
        #     # The tool will be executed again with the user's decision.
        #     tool_context.request_confirmation(
        #         hint=f"You are about to update memory '{person_id}'. Current content: {person_data.get('metadata')}. Do you approve?",
        #         payload={"confirmed": False},
        #     )
        #     # Return a pending status to indicate that the tool is waiting for user input.
        #     return {"status": "pending", "message": "Waiting for user confirmation."}

        # # If a confirmation decision has been made, check the payload.
        # if not tool_confirmation.confirmed:
        #     return {
        #         "status": "cancelled",
        #         "message": "User cancelled the memory update.",
        #     }

        # confirmed = tool_confirmation.confirmed

        # print(f"[CONFIRMED]: {confirmed}", end="\n\n\n")
        # print(f"[TOOL CONFIRMATION]: {tool_confirmation}", end="\n\n\n")
        # print(f"[TOOL CONTEXT]: {tool_context}", end="\n\n\n")

        # if confirmed:
        if True:
            # --- User has approved, so proceed with the update ---
            records = {key: value for key, value in updates.items()}
            records["updated_at"] = int(datetime.now().timestamp())
            existing_records = person_to_update.vectors[person_id].to_dict()
            if existing_records:
                metadata = existing_records.get("metadata", {})
                existing_user_ids = [
                    x["id_value"] for x in json.loads(metadata["user_ids"])
                ]

                if "user_ids" in updates:
                    new_user_ids = [x["id_value"] for x in updates["user_ids"]]
                    existing_user_ids.extend(new_user_ids)
                    updated_user_ids_str = ", ".join(existing_user_ids)
                    records["text"] = (
                        f"{metadata['first_name']} {metadata['last_name']} IDs {updated_user_ids_str}"
                    )

            _ = index.update(id=person_id, namespace=namespace, set_metadata=records)

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
        # else:
        #     tool_context.actions.escalate
        #     return {
        #         "status": "cancelled",
        #         "message": "User cancelled the memory update.",
        #     }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def get_records_by_id(
    tool_context: ToolContext, record_ids: list[str], namespace: str
) -> dict:
    """
    Fetches one or several memories or people from Pinecone using their respective memory / person IDs.

    Args:
        tool_context (ToolContext): a ToolContext object.
        record_ids (list[str]): Required. A list of memory_id strings.
        namespace (str): Required. The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience).

    Returns:
        dict: The result of the upsert operation.
    """
    user_id = tool_context.state.get("user_id")
    if namespace == "personal" and user_id not in config.SUPERUSERS:
        return {
            "status": "restricted",
            "search_results": "sorry, personal memories are for my master user only",
        }
    if namespace == "professional" and (
        user_id not in config.SUPERUSERS
        and not user_id.lower().endswith(config.TEAM_DOMAIN)
    ):
        return {
            "status": "restricted",
            "search_results": f"sorry, this information is only available to {config.TEAM_DOMAIN} members",
        }

    try:
        if not namespace or not isinstance(record_ids, list):
            return {
                "status": "error",
                "message": "`record_ids` MUST be a list of memory id strings, namespace must be provided",
            }
        index = pc.Index(index_name)
        vectors = index.fetch(ids=record_ids, namespace=namespace)
        records_data = {key: value.metadata for key, value in vectors.vectors.items()}
        return {"status": "success", "memories": records_data}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def delete_memory(tool_context: ToolContext, namespace: str, record_id: str):
    """
    Deletes a specific record from  a specific Pinecone index.

    Args:
        namespace (str): The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience)..
        record_id (str): An ID of the record to delete.

    Returns:
        dict: The result of the delete operation.
    """
    user_id = tool_context.state.get("user_id")
    if user_id not in config.SUPERUSERS:
        return {
            "status": "restricted",
            "message": "sorry, only master user can perform delete operations right now",
        }
    try:
        index = pc.Index(index_name)
        _ = index.delete(ids=[record_id], namespace=namespace)
        check = index.fetch([record_id], namespace=namespace)
        if check and check.vectors:
            return {
                "status": "failed",
                "message": f"record {record_id} still exists in {namespace}",
            }
        return {
            "status": "success",
            "message": f"record {record_id} successfully deleted from {namespace}",
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def search_memories(
    tool_context: ToolContext, namespace: str, search_query: str, top_k: int
):
    """
    Searches for memories/records in Pinecone using a search query.

    Args:
        namespace (str): The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience)..
        search_query (str): The search query to search in Pinecone records
        top_k (int): How many results to return. Start with small numbers (3-5) and only increase this number if you want to do a broader search.

    Returns:
        dict: The result of the search operation along with additional metadata (if any).

    """

    user_id = tool_context.state.get("user_id")
    if namespace == "personal" and user_id not in config.SUPERUSERS:
        return {
            "status": "restricted",
            "search_results": "sorry, personal memories are for my master user only",
        }
    elif user_id not in config.SUPERUSERS and not user_id.lower().endswith(
        config.TEAM_DOMAIN
    ):
        return {
            "status": "restricted",
            "search_results": f"sorry, this information is only available to {config.TEAM_DOMAIN} members",
        }
    try:
        query = SearchQuery(inputs={"text": search_query}, top_k=top_k)

        index = pc.Index(index_name)
        results = index.search(namespace=namespace, query=query)
        if results:
            summary = results.to_dict().get("result", {}).get("hits")
            return {"status": "success", "search_results": summary}
        return {"status": "failed", "search_results": results.result}
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
        # FunctionTool(create_memory, require_confirmation=True),
        create_memory,
        update_memory,
        create_people,
        update_people,
        delete_memory,
        get_records_by_id,
        search_memories,
    ]  # , search_records, delete_record]
