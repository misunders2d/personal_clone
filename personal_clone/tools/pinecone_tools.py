import json
import time
import uuid
from datetime import datetime

from google.adk.tools.tool_context import ToolContext
from pinecone import FetchResponse, IndexModel, PineconeAsyncio, SearchQuery, Vector

# from google.adk.tools.function_tool import FunctionTool
from .. import config
from ..tools.session_state_tools import extract_user_ids_from_tool_context

pc = PineconeAsyncio(api_key=config.PINECONE_API_KEY)
index_name = config.PINECONE_INDEX_NAME


async def list_indexes() -> dict:
    """
    Lists all available indexes in Pinecone

    Returns:
        dict: The result of the list_indexes operation.

    """
    try:
        index_names_future = await pc.list_indexes()
        index_names = index_names_future.names()
        return {"status": "success", "index_names": index_names}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_records_by_id(
    tool_context: ToolContext, record_ids: list[str], namespace: str, format: str
) -> dict:
    """
    Fetches one or several memories or people from Pinecone using their respective memory / person IDs.

    Args:
        tool_context (ToolContext): a ToolContext object.
        record_ids (list[str]): Required. A list of memory_id strings - accepts multiple records.
        namespace (str): Required. The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience).
        format (str): Required. "full" to pull full records data (including long description), or "short" (just id, short_description and tags - for quick overview)

    Returns:
        dict: The result of the upsert operation.
    """
    if format not in ("full", "short"):
        return {
            "status": "args error",
            "search_results": "`format` can only be `full` or `short`",
        }
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
        index_descr = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            vectors = await index.fetch(ids=record_ids, namespace=namespace)
            records_data = {
                key: value.metadata for key, value in vectors.vectors.items()
            }
            if records_data and format == "full":
                return {"status": "success", "memories": records_data}
            elif records_data and format == "short":
                short_data = {
                    key: {
                        "category": value.get("category") if value else None,
                        "short_description": (
                            value.get("short_description") if value else None
                        ),
                        "tags": value.get("tags") if value else None,
                    }
                    for key, value in records_data.items()
                }
                return {"status": "success", "memories": short_data}
            else:
                return {
                    "status": "failed",
                    "memories": f"no records with id {record_ids} found",
                }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def list_records(tool_context: ToolContext, namespace: str) -> dict:
    """
    Fetches all memories/records from a namespace in Pinecone index.
    The function specifically fetches the memory_id, category, short_description and tags.

    Args:
        namespace (str): The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience)..
        top_k (int): How many results to return. Start with small numbers (3-5) and only increase this number if you want to do a broader search.

    Returns:
        dict: The result of the fetch operation along with memory_id, category, short_description and tags of records.

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

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        full_results = []
        async with pc.IndexAsyncio(index_descr.host) as index:
            results = await index.list_paginated(namespace=namespace, limit=20)
            full_results.extend(results.vectors)
            while results.pagination:
                results = await index.list_paginated(
                    namespace=namespace, pagination_token=results.pagination.next
                )
                full_results.extend(results.vectors)
            if full_results:
                mem_ids = [x["id"] for x in full_results]
                memories = await get_records_by_id(
                    tool_context,
                    record_ids=mem_ids,
                    namespace=namespace,
                    format="short",
                )
                return {"status": "success", "search_results": memories}
            return {"status": "failed", "search_results": "nothing found"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def confirmed(tool_context: ToolContext):

    if (
        tool_context.user_content
        and tool_context.user_content.parts
        and tool_context.user_content.parts[0]
        and tool_context.user_content.parts[0].text
    ):
        last_user_message = tool_context.user_content.parts[0].text
        if "YES" in last_user_message:
            return True
    return False


async def create_memory(
    tool_context: ToolContext,
    namespace: str,
    text: str,
    short_description: str,
    category: str,
    tags: list[str],
    related_people: list[str] = [],
    related_memories: str = "[]",
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
        related_memories (str): Optional. A JSON string representing a list of references to other memories. Example: '''[{"related_memory_id": "mem_...", "relation_type": "related_to"}]'''. Defaults to an empty list string "[]".

    Returns:
        dict: The result of the upsert operation.

    Example:
        records = '''[
            {
                "memory_id": None,
                "short_description": "Call with Bernard about promotion",
                "text": "Bernard suggested I consider a raise and work toward Sales Director. Discuss with Igor and Margarita.",
                "category": "strategy",
                "tags": ["career", "raise"],
                "related_people": ["per_2025_09_16_c08e0ed4", "per_2025_10_02_41c37001"],
                "related_memories": None,
            }
        ]'''
    """

    if not await confirmed(tool_context):
        arg_dict = {
            "namespace": namespace,
            "text": text,
            "short_description": short_description,
            "category": category,
            "tags": tags,
            "related_people": related_people,
            "related_memories": related_memories,
        }
        return {
            "status": "requires confirmation",
            "message": "Memory creation must be confirmed by user. The user must explicitly confirm by replying with `YES`.",
            "args": arg_dict,
        }

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
        related_memories_list = json.loads(related_memories) if related_memories else []

        date_value = datetime.now()
        memory_id = f"mem_{date_value.strftime('%Y_%m_%d')}_{uuid.uuid4().hex}"

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
        if related_memories_list:
            single_record["related_memories"] = json.dumps(related_memories_list)

        records = [single_record]

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            await index.upsert_records(namespace=namespace, records=records)

            # verifying that memory was updated/created
            attempts = 0
            check = FetchResponse(namespace=namespace, vectors={}, usage = None)
            while attempts < 10 and not check.vectors:  # type: ignore
                check = await index.fetch(
                    ids=[x["id"] for x in records], namespace=namespace
                )
                time.sleep(1.5)

        if check and check.vectors:
            return {
                "status": "success",
                "response": f"id {records[0].get('id')} successfully created in {namespace} namespace",
            }
        else:
            return {
                "status": "failed",
                "response": f"id {records[0].get('id')} not created in {namespace}",
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def create_people(
    tool_context: ToolContext,
    first_name: str,
    last_name: str,
    role: str,
    user_ids: str,
    relations: str = "[]",
) -> dict:
    """
    A dedicated function to create records about people, one person at a time.

    Args:
        - tool_context (ToolContext): a ToolContext object.
        - first_name (str): Required. Person's first name.
        - last_name (str): Required. Person's last name. Use an empty string ("") if last name is unknown, but it is highly recommended to find out the user's last name to avoid ambiguity.
        - role (str): Required. Short description of the role or how this person is perceived and related to the "owner" user. Example: 'friend', 'mentor', 'colleague'.
        - user_ids (str): Required. A JSON string of identifiers for the person. Example: '''[{"id_type":"personal email","id_value":"user@example.com"},{"id_type":"telegram handle","id_value":"@tg_user"}]'''.
        - relations (str): Optional. A JSON string of connections to other people. Example: '''[{"related_person_id":"per_abc123","relation_type":"son"}]'''. Defaults to an empty list string "[]".

    Returns:
        dict: The result of the upsert operation.

    """

    if not await confirmed(tool_context):
        arg_dict = {
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "user_ids": user_ids,
            "relations": relations,
        }
        return {
            "status": "requires confirmation",
            "message": "Memory creation must be confirmed by user. The user must explicitly confirm by replying with `YES`.",
            "args": arg_dict,
        }

    try:
        namespace = "people"
        # user_id = tool_context.state.get("user_id", "unknown_user")

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

        date_value = datetime.now()
        person_id = f"per_{date_value.strftime('%Y_%m_%d')}_{uuid.uuid4().hex}"

        user_ids_list = json.loads(user_ids) if user_ids else []
        relations_list = json.loads(relations) if relations else []

        # actual memory creation or update
        user_ids_str = ", ".join([x["id_value"] for x in user_ids_list])
        single_record = {
            "id": person_id,
            "created_at": int(date_value.timestamp()),
            "first_name": first_name,
            "last_name": last_name,
            "text": f"{first_name} {last_name}. IDs: {user_ids_str}".strip(),
            "role": role,
            "user_ids": json.dumps(user_ids_list),
        }
        if relations_list:
            single_record["relations"] = json.dumps(relations_list)

        records = [single_record]

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            await index.upsert_records(namespace=namespace, records=records)
            # verifying that memory was updated/created
            attempts = 0
            check = FetchResponse(namespace=namespace, vectors={}, usage = None)
            while attempts < 10 and not check.vectors:  # type: ignore
                check = await index.fetch(
                    ids=[x["id"] for x in records], namespace=namespace
                )
                time.sleep(1.5)

        if check and check.vectors:
            return {
                "status": "success",
                "response": f"person {records[0].get('id')} ({first_name} {last_name}) successfully updated in {namespace} namespace",
            }
        else:
            return {
                "status": "failed",
                "response": f"person {records[0].get('id')} ({first_name} {last_name}) not inserted to {namespace}",
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def update_memory(
    tool_context: ToolContext, namespace: str, memory_id: str, updates: str = "{}"
) -> dict:

    if not await confirmed(tool_context):
        arg_dict = {
            "namespace": namespace,
            "memory_id": memory_id,
            "updates": updates,
        }
        return {
            "status": "requires confirmation",
            "message": "Memory update must be confirmed by user. The user must explicitly confirm by replying with `YES`.",
            "args": arg_dict,
        }

    """
    Modifies/updates a specific record in a specific Pinecone namespace.

    Args:
        tool_context (ToolContext): a ToolContext object.
        namespace (str): Required. The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience).
        memory_id (str): Required. memory_id string.
        updates (str): Required. A JSON string representing a dictionary of updates to apply. The dictionary MUST CONTAIN AT LEAST ONE OF THE FOLLOWING keys:
            - "text" (str): the main content/body of the memory to update.
            - "short_description" (str): short summary/title for the memory to update.
            - "category" (str): one of the allowed categories (e.g., "project", "memory", "strategy", "note", "task", "professional").
            - "tags" (list[str]): list of keyword tags to update.
            - "related_people" (list[str]): list of person ids (e.g., "per_2025_09_05_8909994f") referenced by this memory to update.
            - "related_memories" (list of objects): references to other memories, e.g., '''[{"related_memory_id": "mem_...", "relation_type": "related_to"}]'''.


    Returns:
        dict: The result of the upsert operation.

    Example (update):
        updates = '''{"short_description": "Call with Bernard about promotion (updated)","text": "Updated notes: Bernard suggested a raise...","tags": ["career", "raise", "promotion"]}'''

    """

    try:
        updates_dict = json.loads(updates)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON string for `updates`: {e}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    allowed_fields = (
        "text",
        "short_description",
        "category",
        "tags",
        "related_people",
        "related_memories",
    )
    if not isinstance(updates_dict, dict) or not updates_dict:
        return {
            "status": "error",
            "message": f"`updates` must be a JSON string representing a dict with at least one of the allowed values: {allowed_fields}",
        }
    if any(key not in allowed_fields for key in updates_dict.keys()):
        return {"status": "error", "message": "forbidden keys in the `updates` dict"}

    current_user_ids_dict = extract_user_ids_from_tool_context(tool_context)

    if current_user_ids_dict.get("status") == "success":
        current_user_ids = current_user_ids_dict["user_ids"]
    else:
        return {"status": "error", "message": current_user_ids_dict.get("message")}

    try:
        # records = {key: value for key, value in updates_dict.items()}
        records = updates_dict.copy()
        records["updated_at"] = int(datetime.now().timestamp())
        if "related_memories" in updates_dict:
            records["related_memories"] = json.dumps(updates_dict["related_memories"])

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            memory_to_update = await index.fetch(ids=[memory_id], namespace=namespace)
            if not memory_to_update.vectors:
                return {
                    "status": "error",
                    "message": f"Memory {memory_id} not found in namespace {namespace}",
                }

            memory_creator = (
                memory_to_update.vectors[memory_id]
                .to_dict()
                .get("metadata", {})
                .get("user_id")
            )

            if memory_creator not in current_user_ids and not any(
                user_id in config.SUPERUSERS for user_id in current_user_ids
            ):
                return {
                    "status": "forbidden",
                    "message": f"Memory {memory_id} was created by {memory_creator} and can only be modified by this user",
                }

            await index.update(id=memory_id, namespace=namespace, set_metadata=records)
        time.sleep(1.5)
        result = await get_records_by_id(
            tool_context=tool_context,
            record_ids=[memory_id],
            namespace=namespace,
            format="full",
        )

        return {
            "status": "needs verification",
            "message": f"Verify that required updates are implemented: {result['memories']}",
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def update_people(
    tool_context: ToolContext, person_id: str, updates: str = "{}"
) -> dict:

    if not await confirmed(tool_context):
        arg_dict = {"person_id": person_id, "updates": updates}
        return {
            "status": "requires confirmation",
            "message": "Memory update must be confirmed by user. The user must explicitly confirm by replying with `YES`.",
            "args": arg_dict,
        }

    """
    Modifies/updates a specific person in "people" Pinecone namespace.

    Args:
        tool_context (ToolContext): a ToolContext object.
        person_id (str): Required. `person_id` string of a specific person to modify.
        updates (str): Required. A JSON string representing a dictionary of updates to apply. The dictionary MUST CONTAIN AT LEAST ONE OF THE FOLLOWING keys:
            - "first_name" (str): Person's first name.
            - "last_name" (str): Person's last name. Use an empty string ("") if last name is unknown, but it is highly recommended to find out the user's last name to avoid ambiguity.
            - "role" (str): Short description of the role or how this person is perceived and related to the "owner" user. Example: 'friend', 'mentor', 'colleague'.
            - "user_ids" (list of objects): Optional. Identifiers for the person, with type labels. Example: '''[{"id_type":"personal email","id_value":"user@example.com"}]'''.
            - "relations" (list of objects): Optional. Connections to other people in the table. Example: '''[{"related_person_id":"per_abc123","relation_type":"son"}]'''.


    Returns:
        dict: The result of the upsert operation.

    Example for 'updates' parameter:
        '''{
            "relations": [{"related_person_id": "per_2025_10_12_elksjdf", "relation_type": "friend"}],
            "user_ids": [{"id_type": "personal email", "id_value": "user@homeserver.com"}],
            "last_name": "Jovanovich"
        }'''

    """
    namespace = "people"
    try:
        updates_dict = json.loads(updates)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON string for `updates`: {e}",
        }

    allowed_fields = (
        "first_name",
        "last_name",
        "role",
        "user_ids",
        "relations",
    )
    if not isinstance(updates_dict, dict) or not updates_dict:
        return {
            "status": "error",
            "message": f"`updates` must be a dict with at least one of the allowed values: {allowed_fields}",
        }
    if any(key not in allowed_fields for key in updates_dict.keys()):
        return {"status": "error", "message": "forbidden keys in the `updates` dict"}

    current_user_ids_dict = extract_user_ids_from_tool_context(tool_context)

    if current_user_ids_dict.get("status") == "success":
        current_user_ids = current_user_ids_dict["user_ids"]
    else:
        return {"status": "error", "message": current_user_ids_dict.get("message")}

    try:
        # records = {key: value for key, value in updates_dict.items()}
        records = updates_dict.copy()
        records["updated_at"] = int(datetime.now().timestamp())
        if "relations" in updates_dict:
            records["relations"] = json.dumps(updates_dict["relations"])

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            person_to_update = await index.fetch(ids=[person_id], namespace=namespace)
            if not person_to_update.vectors:
                return {
                    "status": "error",
                    "message": f"Person {person_id} not found in namespace {namespace}",
                }

            person_ids_dict = (
                person_to_update.vectors[person_id]
                .to_dict()
                .get("metadata", {})
                .get("user_ids", {})
            )
            person_ids = [x["id_value"] for x in json.loads(person_ids_dict)]

            if not any(
                user_id in person_ids for user_id in current_user_ids
            ) and not any(
                user_id in config.SUPERUSERS for user_id in current_user_ids
            ):
                return {
                    "status": "forbidden",
                    "message": f"Person {person_id}  can only be modified by this user or superusers",
                }

            await index.update(id=person_id, namespace=namespace, set_metadata=records)

        time.sleep(1.5)
        result = await get_records_by_id(
            tool_context=tool_context,
            record_ids=[person_id],
            namespace=namespace,
            format="full",
        )

        return {
            "status": "needs verification",
            "message": f"Verify that required updates are implemented: {result['memories']}",
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def delete_memory(
    tool_context: ToolContext, namespace: str, record_id: str
) -> dict:

    if not await confirmed(tool_context):
        arg_dict = {"namespace": namespace, "record_id": record_id}
        return {
            "status": "requires confirmation",
            "message": "Memory deletion must be confirmed by user. The user must explicitly confirm by replying with `YES`.",
            "args": arg_dict,
        }

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
        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            await index.delete(ids=[record_id], namespace=namespace)

            attempts = 0
            check = FetchResponse(
                namespace=namespace, vectors={"test": Vector(id="1", values=[1,2,3])}, usage = None
            )
            while attempts < 10 and check.vectors:  # type: ignore
                check = await index.fetch([record_id], namespace=namespace)
                time.sleep(1.5)

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


async def search_memories(
    tool_context: ToolContext, namespace: str, search_query: str, top_k: int
) -> dict:
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

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            results = await index.search_records(namespace=namespace, query=query)
            if results:
                summary = results.to_dict().get("result", {}).get("hits")
                return {"status": "success", "search_results": summary}
            return {"status": "failed", "search_results": "nothing found"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def search_memories_prefetch(
    user_id: str, namespace: str, search_query: str, top_k: int
) -> dict:
    """
    Searches for memories/records in Pinecone using a search query.

    Args:
        namespace (str): The name of the Pinecone index namespace ("personal" for personal memories or "professional" for professional experience)..
        search_query (str): The search query to search in Pinecone records
        top_k (int): How many results to return. Start with small numbers (3-5) and only increase this number if you want to do a broader search.

    Returns:
        dict: The result of the search operation along with additional metadata (if any).

    """

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

        index_descr: IndexModel = await pc.describe_index(index_name)
        if not index_descr or not index_descr.host:
            return {"status": "failed", "error": f"Could not get index description for {index_name}"}
        async with pc.IndexAsyncio(index_descr.host) as index:
            results = await index.search_records(namespace=namespace, query=query)
            if results:
                summary = results.to_dict().get("result", {}).get("hits")
                return {"status": "success", "search_results": summary}
            return {"status": "failed", "search_results": "nothing found"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def get_person_from_search(search_results: list[dict], user_id: str):
    """
    A helper function to extract person records from search results.
    Args:
        search_results (dict): The search results returned by the search_memories function.

    Returns:
        dict: A dictionary containing person records.
    """
    try:
        results = (
            [
                x
                for x in search_results
                if user_id in x.get("fields", {}).get("user_ids")
            ]
            if search_results
            else None
        )
        if results:
            person_data = results[0].copy()
            for key, value in person_data.get("fields", {}).items():
                if key in ("user_ids", "relations") and value:
                    person_data["fields"][key] = json.loads(value)
            return person_data
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# def run_tool_confirmation_test(tool_context: ToolContext) -> dict:
#     """
#     A test function to verify the tool confirmation flow
#     """

#     tool_confirmation = tool_context.tool_confirmation
#     if not tool_confirmation:
#         print("[REQUESTING TOOL CONFIRMATION]", end="\n\n\n")
#         tool_context.request_confirmation(
#             hint=f"Please confirm the execution of {tool_context.agent_name} tool call",
#             # payload={"approve": False},
#         )

#         print(
#             {"status": "pending", "message": "waiting for user confirmation"},
#             end="\n\n\n",
#         )
#         return {"status": "pending", "message": "waiting for user confirmation"}

#     if tool_context.tool_confirmation and tool_context.tool_confirmation.confirmed:
#         print("[CONFIRMED TOOL CONFIRMATION]", end="\n\n\n")
#         return {"status": "completed", "message": "user confirmation received"}

#     else:
#         return {"status": "incomplete", "message": "confirmation was never requested"}


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
        list_records,
        # FunctionTool(run_tool_confirmation_test, require_confirmation=True)
    ]  # , search_records, delete_record]
