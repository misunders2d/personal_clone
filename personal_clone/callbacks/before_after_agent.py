from google.adk.agents.callback_context import CallbackContext
from typing import Optional
from google.genai import types


def check_if_agent_should_run(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Logs entry and checks 'answer_needed' in session state.
    If True, returns Content to skip the agent's execution.
    If False or not present, returns None to allow execution.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()

    # Check the condition in session state dictionary
    if current_state.get("answer_needed", "TRUE").strip() == "FALSE":
        # Return Content to skip the agent's run
        return types.Content(
            # parts=[types.Part(text="")],
            parts=None,
            role="model",  # Assign model role to the overriding response
        )
    else:
        # Return None to allow the LlmAgent's normal execution
        return None


def memory_state_management(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Logs entry and checks 'answer_needed' in session state.
    If True, returns Content to skip the agent's execution.
    If False or not present, returns None to allow execution.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    if "memories_combined" not in callback_context.state.to_dict():
        callback_context.state["memories_combined"] = []
    if "vertex_search_combined" not in callback_context.state.to_dict():
        callback_context.state["vertex_search_combined"] = []
    current_state = callback_context.state.to_dict()
    combined_memories = current_state.get("memories_combined", [])
    combined_vertex_refs = current_state.get("vertex_search_combined", [])

    if (
        "memory_search" in current_state
        and current_state["memory_search"] not in combined_memories
    ):
        callback_context.state["memories_combined"].append(
            current_state["memory_search"]
        )

    if (
        "vertex_search" in current_state
        and current_state["vertex_search"] not in combined_vertex_refs
    ):
        callback_context.state["vertex_search_combined"].append(
            current_state["vertex_search"]
        )

    return None
