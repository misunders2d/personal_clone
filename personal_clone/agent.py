from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import AgentTool
from google.adk.planners import BuiltInPlanner
from google.genai import types

from .sub_agents.memory_agent import memory_agent
from .sub_agents.vertex_search_agent import vertex_search_agent, vertex_toolset
from .callbacks.before_after_agent import check_if_agent_should_run, state_setter

from .callbacks.before_after_agent import memory_state_management


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
    HOWEVER if the user is explicilty demanding an answer, you ALWAYS reply with "TRUE".
    You reply ONLY with "TRUE" if the answer is needed or "FALSE", nothing else.
    """,
    output_key="answer_needed",
    before_agent_callback=[state_setter],
)


memory_validator_agent = Agent(
    name="memory_validator_agent",
    description="Checks the user input and decides whether or not to call the memory agents",
    model="gemini-2.0-flash-lite",
    instruction="""You are an agent designed to assess the user's input.
    Your ONLY job is to decide whether or not the `personal_clone` agent should use its memory tools before answering the user's query.
    That includes creating new memories, recalling memories, modifying or deleting them.
    You reply ONLY with "USE MEMORY" or "DON'T USE MEMORY", nothing else.
    """,
    output_key="use_memory",
    # before_agent_callback=[check_if_agent_should_run],
)

starter_agent = ParallelAgent(
    name="starter_agent",
    description="Validator agent which runs prior to main agent's logic. Designed to alter {use_memory} and {answer_needed} state keys.",
    sub_agents=[answer_validator_agent, memory_validator_agent],
)

main_agent = Agent(
    model="gemini-2.5-flash",
    name="personal_clone",
    description="A helpful assistant for user questions.",
    instruction="""
    <GENERAL>
        - You are an assistant, a secretary and a second brain for the person whose ID is {user_id}.
        - You learn from the communication with this user, copy their style.
        - You are equipped with different sub-agents and tools that help you manage the conversation. Specific tools are used to store and retrieve memories and experiences - use them widely.
    </GENERAL>
    <IMPORTANT!>
        <MEMORY USAGE>
            - If {use_memory} says exactly "USE MEMORY":
                - First, you must check {memories_combined} and {vertex_search_combined} to see if the discussed topic is already in the memory context.
                - If the topic is not found in state, you MUST use your memory tools (first `memory_agent` and if no relevant memories are found - then `vertex_search_agent`) to pull relevant data and answer the question in the most effective manner.
                    - Use the EXACT query the user submitted, even if you think it's too vague or requires more details.
        </MEMORY USAGE>
        <ERROR HANDLING>
            - If you receive an error message from any of the tools or sub-agents - you MUST follow the <MEMORY USAGE> protocol. Only if such an error is not found in memories, should you seek guidance from the user.
            - After the issue has been successfully resolved - you MUST use the `memory_agent` to remember (save) this experience, so that you can refer to it later.
        </ERROR HANDLING>
    </IMPORTANT!> 
    <Troubleshooting and Learning>
        - Whenever you encounter any issues or difficulties (running functions, user's frustration, syntax errors, unexpected outputs, or logical problems),
            you shall first consult the stored memories. You will specifically look up relevant memories where the `user_id` is "agent".
            This self-reflection and learning from past experiences will enable faster problem identification and resolution.
            This includes reviewing previous errors, successful solutions, and operational notes.
        - If the remembered solution is outdated or not applicable, you should adapt it to the current context and update that memory with the new solution.
        - If the solution is not found in the memories, you can then proceed to ask for help from the user.
            Make sure to save this new knowledge in the memories for future reference.
    </Troubleshooting and Learning>

    """,
    tools=[get_current_datetime, AgentTool(vertex_search_agent)],
    sub_agents=[memory_agent],
    before_agent_callback=[check_if_agent_should_run],
    after_agent_callback=[memory_state_management],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)
    ),
)


root_agent = SequentialAgent(
    name="root_agent_flow",
    description="A sequence of agents utilizing a helper agent which decides whether or not to use memory tools",
    sub_agents=[starter_agent, main_agent],
)
