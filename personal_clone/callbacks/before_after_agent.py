from google.adk.agents.callback_context import CallbackContext
from typing import Optional
from google.genai import types
from concurrent.futures import ThreadPoolExecutor


from ..tools.search_tools import search_bq, MEMORY_TABLE, MEMORY_TABLE_PROFESSIONAL


def state_setter(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """sets initial state"""

    current_state = callback_context.state.to_dict()
    current_user = callback_context._invocation_context.user_id

    if "user_id" not in current_state:
        callback_context.state["user_id"] = current_user
        # callback_context.state["user_id"] = (
        #     "2djohar@gmail.com"  # TODO change to `current_user` for production
        # )
    if "memory_context" not in current_state:
        callback_context.state["memory_context"] = ""
    if "memory_context_professional" not in current_state:
        callback_context.state["memory_context_professional"] = ""
    if "vertex_context" not in current_state:
        callback_context.state["vertex_context"] = ""


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
    Logs exit from an agent and checks 'add_concluding_note' in session state.
    If True, returns new Content to *replace* the agent's original output.
    If False or not present, returns None, allowing the agent's original output to be used.
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
        with ThreadPoolExecutor() as pool:
            personal_future = pool.submit(search_bq, MEMORY_TABLE, last_user_message)
            professional_future = pool.submit(
                search_bq, MEMORY_TABLE_PROFESSIONAL, last_user_message
            )
            memory_recall = personal_future.result()
            memory_recall_professional = professional_future.result()

        callback_context.state["memory_context_professional"] = (
            memory_recall_professional
        )

        if not user_id == "2djohar@gmail.com":
            return

        callback_context.state["memory_context"] = memory_recall
        callback_context.state["vertex_context"] = ""  # TODO add vertex search here
