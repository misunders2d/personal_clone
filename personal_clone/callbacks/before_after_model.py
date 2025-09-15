from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse

from google.adk.models.llm_request import LlmRequest
from typing import Optional
from google.genai import types
import json
from json import JSONDecodeError


def create_default_response(message="") -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    text=json.dumps(
                        {
                            "result": "PASS",
                            "topic": "PASS",
                            "content": f"PASS {message}".strip(),
                            "related_memories": [],
                            "related_people": [],
                        }
                    )
                )
            ],
        ),
    )


def recall_agents_stopper(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    if (
        llm_request.contents
        and llm_request.contents[-1].role == "user"
        and llm_request.contents[-1].parts
    ):
        if (
            llm_request.contents[-1].parts[0].text
            and "memory_agent" in llm_request.contents[-1].parts[0].text
        ):
            return create_default_response()


def recall_agents_checker(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    # agent_name = callback_context.agent_name

    # if agent_name in ("memory_recall_agent", "vertex_recall_agent"):
    #     pass

    if (
        llm_response.content
        and llm_response.content.parts
        and llm_response.content.parts[0].text
    ):
        try:
            original_text = json.loads(llm_response.content.parts[0].text)
            if "result" not in original_text or original_text["result"] == "PASS":
                return create_default_response()
        except JSONDecodeError as e:
            return create_default_response(str(e))

    else:
        return None
