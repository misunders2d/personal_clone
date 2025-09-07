from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import AgentTool

from .sub_agents.memory_agent import memory_agent, bigquery_toolset
from .sub_agents.vertex_search_agent import vertex_search_agent, vertex_toolset
from .callbacks.before_after_agent import check_if_agent_should_run

from dotenv import load_dotenv

load_dotenv()


def get_current_datetime():
    from datetime import datetime

    return datetime.now().isoformat()


answer_validator_agent = Agent(
    name="answer_validator_agent",
    description="Checks the user input and decides whether or not the user's question actually requires a response",
    model="gemini-2.0-flash-lite",
    instruction="""You are an agent designed to assess the user's input.
    Your ONLY job is to decide whether or not the `personal_clone` agent should reply to the user's query.
    Quite often the user's resonse does not require an answer, like "okay", "bye" etc.
    You reply ONLY with "TRUE" if the answer is needed or "FALSE", nothing else.
    """,
    output_key="answer_needed",
)


memory_validator_agent = Agent(
    name="memory_validator_agent",
    description="Checks the user input and decides whether or not to call the memory agents",
    model="gemini-2.0-flash-lite",
    instruction="""You are an agent designed to assess the user's input.
    Your ONLY job is to decide whether or not the `personal_clone` agent should use its memory tools before answering the user's query.
    You reply ONLY with "USE MEMORY" or "don't use memory", nothing else.
    """,
    output_key="use_memory",
    before_agent_callback=[check_if_agent_should_run],
)


main_agent = Agent(
    model="gemini-2.5-flash",
    name="personal_clone",
    description="A helpful assistant for user questions.",
    instruction="""Answer user questions to the best of your knowledge.
    IMPORTANT! 
        - If {use_memory} says exactly "USE MEMORY" - you MUST use your memory tools (first `memory_agent` and then `vertex_search_agent`) to pull relevant data and answer the question in the most effective manner.
        - If you receive an error message from any of the tools or sub-agents - FIRST thing you need to do is to call `memory_agent` and ask to search for that error in the memories.
            Only if such an error is not found in memories, should you seek guidance from the user.
            After the issue has been successfully resolved - you MUST use the `memory_agent` to remember this experience, so that you can refer to it later.
    """,
    tools=[get_current_datetime],
    sub_agents=[memory_agent, vertex_search_agent],
    before_agent_callback=[check_if_agent_should_run],
)


root_agent = SequentialAgent(
    name="root_agent_flow",
    description="A sequence of agents utilizing a helper agent which decides whether or not to use memory tools",
    sub_agents=[answer_validator_agent, memory_validator_agent, main_agent],
)
