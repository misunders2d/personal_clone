from google.adk.agents.callback_context import CallbackContext
from typing import Optional
from google.genai import types


def check_if_agent_should_run(callback_context: CallbackContext) -> Optional[types.Content]:
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
            parts=[types.Part(text="")],
            role="model" # Assign model role to the overriding response
        )
    else:
        # Return None to allow the LlmAgent's normal execution
        return None
