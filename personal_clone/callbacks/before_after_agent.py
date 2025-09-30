from google.adk.agents.callback_context import CallbackContext
from typing import Optional
from google.genai import types
from concurrent.futures import ThreadPoolExecutor


from ..tools.search_tools import (
    search_bq,
    search_people,
)
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
    if "user_related_context" not in current_state:
        callback_context.state["user_related_context"] = ""
    callback_context.state["current_datetime"] = get_current_datetime()


def check_if_agent_should_run(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Logs entry and checks 'answer_needed' in session state.
    If True, returns Content to skip the agent's execution.
    If False or not present, returns None to allow execution.
    """
    # agent_name = callback_context.agent_name
    # invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()

    if not current_state.get("answer_validation", {}).get("answer_needed"):
        return types.Content(
            # parts=[types.Part(text="")],
            parts=None,
            role="model",  # Assign model role to the overriding response
        )
    else:
        return None


def prefetch_memories(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Used to prefetch personal and professional memories based on the user query.
    Injects records from memories into session state
    """
    last_user_message = ""
    user_id = callback_context.state.get("user_id")

    if (
        callback_context.user_content
        and callback_context.user_content.parts
        and callback_context.user_content.parts[0]
        and callback_context.user_content.parts[0].text
    ):
        last_user_message = callback_context.user_content.parts[0].text
    if callback_context.state.get("answer_validation", {}).get(
        "answer_needed"
    ) and callback_context.state.get("answer_validation", {}).get("rr"):
        people_query = f"""
        SELECT
            person_id,
            first_name,
            last_name,
            role
        FROM
            `personal-clone-464511.memories.people` AS p,
        UNNEST(p.user_ids) AS user_id_alias
        WHERE
            "{user_id}" IN (user_id_alias.id_value)
        """
        with ThreadPoolExecutor() as pool:
            personal_future = pool.submit(
                search_bq, config.MEMORY_TABLE, last_user_message
            )
            professional_future = pool.submit(
                search_bq, config.MEMORY_TABLE_PROFESSIONAL, last_user_message
            )
            people_future = pool.submit(search_people, people_query)

            memory_recall = personal_future.result()
            memory_recall_professional = professional_future.result()
            people_recall = people_future.result()

        callback_context.state["memory_context_professional"] = (
            memory_recall_professional
        )
        callback_context.state["user_related_context"] = people_recall

        if not user_id == "2djohar@gmail.com":
            return

        callback_context.state["memory_context"] = memory_recall
        callback_context.state["vertex_context"] = ""  # TODO add vertex search here
