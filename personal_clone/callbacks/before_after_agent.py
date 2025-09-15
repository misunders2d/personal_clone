from google.adk.agents.callback_context import CallbackContext
from typing import Optional
from google.genai import types


def state_setter(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """sets initial state"""

    current_state = callback_context.state.to_dict()
    current_user = callback_context._invocation_context.user_id
    # if "memories_combined" not in current_state:
    #     callback_context.state["memories_combined"] = []
    # if "vertex_search_combined" not in current_state:
    #     callback_context.state["vertex_search_combined"] = []
    if "user_id" not in current_state:
        callback_context.state["user_id"] = (
            current_user  # TODO change to `current_user` for production
        )
        callback_context.state["user_id"] = (
            "2djohar@gmail.com"  # TODO change to `current_user` for production
        )


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

    if current_state.get("answer_needed", "TRUE").strip() == "FALSE":
        return types.Content(
            # parts=[types.Part(text="")],
            parts=None,
            role="model",  # Assign model role to the overriding response
        )
    else:
        return None
