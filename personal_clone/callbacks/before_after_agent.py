from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext
from typing import Optional
from google.genai import types
from concurrent.futures import ThreadPoolExecutor


# from ..tools.search_tools import (
#     search_bq,
#     search_people,
# )

from ..tools.pinecone_tools import search_memories
from ..tools.datetime_tools import get_current_datetime

from .. import config


def state_setter(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """sets initial state"""

    current_state = callback_context.state.to_dict()
    current_user = callback_context._invocation_context.user_id

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
    callback_context.state["current_datetime"] = get_current_datetime()


def check_if_agent_should_run(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Logs entry and checks 'reply' in session state.
    If True, returns Content to skip the agent's execution.
    If False or not present, returns None to allow execution.
    """
    # agent_name = callback_context.agent_name
    # invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()

    if not current_state.get("answer_validation", {}).get("reply"):
        return types.Content(
            # parts=[types.Part(text="")],
            parts=None,
            role="model",  # Assign model role to the overriding response
        )
    else:
        return None


def professional_agents_checker(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
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


def personal_agents_checker(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """checks if the user is in superusers and prevents agent run with personal memories access"""
    current_state = callback_context.state.to_dict()
    user_id = current_state.get("user_id", "")
    if user_id not in config.SUPERUSERS:
        return types.Content(
            parts=[types.Part(text="Sorry, this agent can run only for master user")],
            role="model",  # Assign model role to the overriding response
        )


def prefetch_memories(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Used to prefetch personal and professional memories based on the user query.
    Injects records from memories into session state
    """
    last_user_message = ""
    user_id = callback_context.state.get("user_id")

    tool_context = ToolContext(invocation_context=callback_context._invocation_context)

    if (
        callback_context.user_content
        and callback_context.user_content.parts
        and callback_context.user_content.parts[0]
        and callback_context.user_content.parts[0].text
    ):
        last_user_message = callback_context.user_content.parts[0].text
    if callback_context.state.get("answer_validation", {}).get("reply"):

        if (
            not user_id.lower().endswith(config.TEAM_DOMAIN)
            and user_id not in config.SUPERUSERS
        ):
            return

        with ThreadPoolExecutor() as pool:

            if user_id in config.SUPERUSERS:
                personal_future = pool.submit(
                    search_memories, tool_context, "personal", last_user_message, 1
                )
            else:
                personal_future = None
            if (
                user_id.lower().endswith(config.TEAM_DOMAIN)
                or user_id in config.SUPERUSERS
            ):
                professional_future = pool.submit(
                    search_memories, tool_context, "professional", last_user_message, 1
                )
            else:
                professional_future = None

            people_future = pool.submit(
                search_memories, tool_context, "people", user_id, 1
            )

            memory_recall = personal_future.result() if personal_future else None
            memory_recall_professional = (
                professional_future.result() if professional_future else None
            )
            people_recall = people_future.result()

        callback_context.state["memory_context_professional"] = (
            memory_recall_professional.get("search_results")
            if memory_recall_professional
            else None
        )

        callback_context.state["memory_context"] = (
            memory_recall.get("search_results") if memory_recall else None
        )
        callback_context.state["user_related_context"] = (
            people_recall.get("search_results") if people_recall else None
        )
        callback_context.state["vertex_context"] = ""  # TODO add vertex search here
