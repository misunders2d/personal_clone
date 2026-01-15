from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .. import config
from ..tools.datetime_tools import get_current_datetime
from ..tools.pinecone_tools import get_person_from_search, search_memories_prefetch
from ..tools.vertex_tools import search_file_store


async def state_setter(
    callback_context: CallbackContext,
) -> types.Content | None:
    """sets initial state"""

    current_state = callback_context.state.to_dict()
    current_user = callback_context.user_id

    if "master_user_id" not in current_state:
        callback_context.state["master_user_id"] = config.SUPERUSERS
    if "user_id" not in current_state:
        callback_context.state["user_id"] = current_user
    if "memory_context" not in current_state:
        callback_context.state["memory_context"] = ""
    if "memory_context_professional" not in current_state:
        callback_context.state["memory_context_professional"] = ""
    if "vertex_context" not in current_state:
        callback_context.state["vertex_context"] = ""
    if "rag_context" not in current_state:
        callback_context.state["rag_context"] = ""
    if "user_related_context" not in current_state:
        callback_context.state["user_related_context"] = ""
    if "google_search_grounding" not in current_state:
        callback_context.state["google_search_grounding"] = {
            "final_answer": None,
            "grounding_medadata": {"grounding_chunks": [], "grounding_supports": []},
        }
    if "clickup_user_info" not in current_state:
        callback_context.state["clickup_user_info"] = {}
    if "current_goals" not in current_state:
        callback_context.state["current_goals"] = {}
    callback_context.state["current_datetime"] = get_current_datetime()


async def check_if_agent_should_run(
    callback_context: CallbackContext,
) -> types.Content | None:
    """
    Logs entry and checks 'reply' in session state.
    If True, returns Content to skip the agent's execution.
    If False or not present, returns None to allow execution.
    """
    current_state = callback_context.state.to_dict()

    if not current_state.get("answer_validation", {}).get("reply"):
        return types.Content(
            parts=None,
            role="model",  # Assign model role to the overriding response
        )
    else:
        return None


async def professional_agents_checker(
    callback_context: CallbackContext,
) -> types.Content | None:
    """checks if the user is in superusers and prevents agent run with personal memories access"""
    current_state = callback_context.state.to_dict()
    user_id = current_state.get("user_id", "")

    if (
        not user_id.lower().endswith(config.TEAM_DOMAIN)
        and user_id not in config.SUPERUSERS
    ):
        return types.Content(
            parts=[
                types.Part(
                    text=f"Sorry, this agent can run only for {config.TEAM_DOMAIN} users"
                )
            ],
            role="model",  # Assign model role to the overriding response
        )


async def personal_agents_checker(
    callback_context: CallbackContext,
) -> types.Content | None:
    """checks if the user is in superusers and prevents agent run with personal memories access"""
    current_state = callback_context.state.to_dict()
    user_id = current_state.get("user_id", "")
    if user_id not in config.SUPERUSERS:
        return types.Content(
            parts=[types.Part(text="Sorry, this agent can run only for master user")],
            role="model",  # Assign model role to the overriding response
        )


async def prefetch_memories(
    callback_context: CallbackContext,
) -> types.Content | None:
    """
    Used to prefetch personal and professional memories based on the user query.
    Injects records from memories into session state
    """

    user_id: str = callback_context.state.get("user_id")

    last_user_message = None

    if (
        callback_context.user_content
        and callback_context.user_content.parts
        and callback_context.user_content.parts[0]
        and callback_context.user_content.parts[0].text
    ):
        last_user_message = callback_context.user_content.parts[0].text
    if (
        callback_context.state.get("answer_validation", {}).get("reply")
        and last_user_message
    ):

        if (
            not user_id.lower().endswith(config.TEAM_DOMAIN)
            and user_id not in config.SUPERUSERS
        ):
            return

        if user_id in config.SUPERUSERS and callback_context.state.get(
            "answer_validation", {}
        ).get("recall"):
            personal_future = search_memories_prefetch(
                user_id, "personal", last_user_message, 1
            )
        else:
            personal_future = None

        if (
            user_id.lower().endswith(config.TEAM_DOMAIN) or user_id in config.SUPERUSERS
        ) and callback_context.state.get("answer_validation", {}).get("recall"):
            professional_future = search_memories_prefetch(
                user_id, "professional", last_user_message, 1
            )
            vertex_future = search_file_store(query=last_user_message, store_name='rag_documents')
        else:
            professional_future = None
            vertex_future = None

        people_future = search_memories_prefetch(user_id, "people", user_id, 3)

        memory_recall = await personal_future if personal_future else None
        memory_recall_professional = (
            await professional_future if professional_future else None
        )
        vertex_recall = await vertex_future if vertex_future else None
        people_recall_results = await people_future
        people_recall = (
            people_recall_results.get("search_results") if people_recall_results else []
        )

        callback_context.state["memory_context_professional"] = (
            memory_recall_professional.get("search_results")
            if memory_recall_professional
            else None
        )

        callback_context.state["memory_context"] = (
            memory_recall.get("search_results") if memory_recall else None
        )
        callback_context.state["user_related_context"] = (
            get_person_from_search(people_recall, user_id) if people_recall else None
        )
        callback_context.state["vertex_context"] = vertex_recall
