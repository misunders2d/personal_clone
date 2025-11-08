from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse

from typing import Optional


async def google_search_grounding(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Saves detailed grounding metadata from Google Search tool calls into the state."""

    grounding_data = {
        "final_answer": None,
        "grounding_medadata": {"grounding_chunks": [], "grounding_supports": []},
    }

    if (
        llm_response.content
        and llm_response.content.parts
        and llm_response.content.parts[0].text
    ):
        grounding_data["final_answer"] = llm_response.content.parts[0].text
    if (
        llm_response.grounding_metadata
        and llm_response.grounding_metadata.grounding_chunks
    ):
        for chunk in llm_response.grounding_metadata.grounding_chunks:
            grounding_data["grounding_medadata"]["grounding_chunks"].append(
                chunk.to_json_dict()
            )
    if (
        llm_response.grounding_metadata
        and llm_response.grounding_metadata.grounding_supports
    ):
        for support in llm_response.grounding_metadata.grounding_supports:
            grounding_data["grounding_medadata"]["grounding_supports"].append(
                support.to_json_dict()
            )

    callback_context.state["google_search_grounding"] = grounding_data
