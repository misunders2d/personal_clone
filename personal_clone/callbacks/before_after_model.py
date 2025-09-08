from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.adk.models.llm_request import LlmRequest
from typing import Optional
from google.genai import types
import json


def memory_model_state_setter(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received. NOT USED"""
    agent_name = callback_context.agent_name
    print(f"[Callback] After model call for agent: {agent_name}")
    if agent_name == "memory_agent":
        output_key = "memory_search"
    elif agent_name == "vertex_search_agent":
        output_key = "vertex_search"
    else:
        output_key = "generic_memory"

    # --- Inspection ---
    original_text = ""

    if (
        llm_response.content
        and llm_response.content.parts
        and llm_response.content.parts[0]
        and llm_response.content.parts[0].function_call
    ):

        for i in range(10):
            print()
        print(llm_response.content.parts[0].function_call)
        for i in range(10):
            print()

    if llm_response.content and llm_response.content.parts:
        # Assuming simple text response for this example
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            print(
                f"[Callback] Inspected original response text: '{original_text[:100]}...'"
            )  # Log snippet
            # callback_context.state[output_key] = llm_response
        if llm_response.content.parts[0].function_call:
            print(
                f"[Callback] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification."
            )
            print("%" * 80)
            print(llm_response.content.parts[0].function_call.args)
            print("%" * 80)
            return None  # Don't modify tool calls in this example
        else:
            print("[Callback] Inspected response: No text content found.")
            return None
    elif llm_response.error_message:
        print(
            f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification."
        )
        return None
    else:
        print("[Callback] Inspected response: Empty LlmResponse.")
        return None  # Nothing to modify

    # # --- Modification Example ---
    # # Replace "joke" with "funny story" (case-insensitive)
    # search_term = "joke"
    # replace_term = "funny story"
    # if search_term in original_text.lower():
    #     print(f"[Callback] Found '{search_term}'. Modifying response.")
    #     modified_text = original_text.replace(search_term, replace_term)
    #     modified_text = modified_text.replace(search_term.capitalize(), replace_term.capitalize()) # Handle capitalization

    #     # Create a NEW LlmResponse with the modified content
    #     # Deep copy parts to avoid modifying original if other callbacks exist
    #     modified_parts = [copy.deepcopy(part) for part in llm_response.content.parts]
    #     modified_parts[0].text = modified_text # Update the text in the copied part

    #     new_response = LlmResponse(
    #          content=types.Content(role="model", parts=modified_parts),
    #          # Copy other relevant fields if necessary, e.g., grounding_metadata
    #          grounding_metadata=llm_response.grounding_metadata
    #          )
    #     print(f"[Callback] Returning modified response.")
    #     return new_response # Return the modified response
    # else:
    #     print(f"[Callback] '{search_term}' not found. Passing original response through.")
    #     # Return None to use the original llm_response
    #     return None
