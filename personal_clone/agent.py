from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import AgentTool
from google.adk.planners import BuiltInPlanner
from google.genai import types

import json

from .sub_agents.memory_agent import (
    create_memory_agent,
    MemoryOutput,
    create_read_instruction,
    WRITE_INSTRUCTION,
    MEMORY_TABLE,
    MEMORY_TABLE_PROFESSIONAL,
)
from .sub_agents.vertex_search_agent import (
    create_vertex_search_agent,
    # VertexMemoryOutput,
)
from .callbacks.before_after_agent import check_if_agent_should_run, state_setter
from .callbacks.before_after_model import recall_agents_checker, recall_agents_stopper

# from .callbacks.before_after_agent import memory_state_management


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

memory_parallel_agent = ParallelAgent(
    name="memory_parallel_agent",
    description="A recall agent running memory recall and vertex search to support the context of the conversation",
    sub_agents=[
        create_memory_agent(
            name="recall_agent_experiences",
            write="blocked",
            instruction=f"""
            <EXTREMELY IMPORTANT!!!>
                - Follow the output schema PRECISELY: {json.dumps(MemoryOutput.model_json_schema(), indent=2)}.
                - Your ONLY mode of operation is SEARCHING MEMORIES, anything beyond that automatically implies "PASS"!
                - You NEVER ask additional questions. If you need to ask any questions, just output "PASS" in all schema fields.
                - If you don't have necessary tools or capabilities to fulfill user's request, your ONLY output must be "PASS" to all schema fields.
            </EXTREMELY IMPORTANT!!!>
            {create_read_instruction(MEMORY_TABLE)}
            """,
            output_schema=MemoryOutput,
            output_key="memory_search",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            planner=None,
            before_model_callback=[recall_agents_stopper],
            after_model_callback=[recall_agents_checker],
        ),
        create_memory_agent(
            name="recall_agent_professional_experiences",
            write="blocked",
            instruction=f"""
            <EXTREMELY IMPORTANT!!!>
                - Follow the output schema PRECISELY: {json.dumps(MemoryOutput.model_json_schema(), indent=2)}.
                - Your ONLY mode of operation is SEARCHING MEMORIES, anything beyond that automatically implies "PASS"!
                - You NEVER ask additional questions. If you need to ask any questions, just output "PASS" in all schema fields.
                - If you don't have necessary tools or capabilities to fulfill user's request, your ONLY output must be "PASS" to all schema fields.
            </EXTREMELY IMPORTANT!!!>
            {create_read_instruction(MEMORY_TABLE_PROFESSIONAL)}
            """,
            output_schema=MemoryOutput,
            output_key="memory_search_professional",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            planner=None,
            before_model_callback=[recall_agents_stopper],
            after_model_callback=[recall_agents_checker],
        ),
        create_vertex_search_agent(
            name="recall_agent_vertex",
            # output_schema=VertexMemoryOutput,
            output_key="vertex_search",
            before_model_callback=[recall_agents_stopper],
        ),
    ],
    before_agent_callback=[check_if_agent_should_run],
)

summary_agent = Agent(
    name="summary_agent",
    description="agent that summarizes information from memory search agents.",
    instruction="""
    You are a summarizer agent designed to recap the memories from {memory_search}, {memory_search_professional} and {vertex_search} session keys.
    Make sure to output the information in a concise manner, but keep all the necessary details, including people ids, memory ids,
    mentions of specific events, details, etc.
    Summarize it in three sections:
    {memory_search} should start with "MEMORY SEARCH:", {memory_search_professional} should start with "MEMORY SEARCH PROFESSIONAL:",and {vertex_search} should start with "VERTEX SEARCH:"
    IMPORTANT!
        If either of the outputs say anything about "I can't update memories, I'm read-only" etc
        OR
        if they don't output search results, you replace their output in your summary with a simple "PASS", nothing else.
    """,
    model="gemini-2.5-flash-lite",
    output_key="memory_recap",
    before_agent_callback=[check_if_agent_should_run],
)

main_agent = Agent(
    model="gemini-2.5-flash",
    name="personal_clone",
    description="A helpful assistant for user questions.",
    instruction="""
    <TOP PRIORITY>
        User's requests are ALWAYS top priority. No matter what is in the conversational context, you always obey the user's commands.
    </TOP PRIORITY>
    <GENERAL>
        - You are an assistant, a secretary and a second brain for the person whose ID is {user_id}.
        - You learn from the communication with this user, copy their style.
        - You are equipped with different sub-agents and tools that help you manage the conversation. Specific tools are used to store and retrieve memories and experiences - use them widely.
        - Your `memory_agent` has access to all personal experiences, and your `memory_agent_professional` has access to all professional experiences. Use them accordingly.
    </GENERAL>
    <IMPORTANT!>
        <MEMORY USAGE>
            - You are equipped with a system of agents who fetch knowledge and memories based on the user's input BEFORE you start your communication.
                Refer to {memory_recap} to make your conversation as context-aware, as possible, but make sure to only refer to it. ALL user commands override this recap, make sure to prioritize the user before that context.
            - If the user is explicitly asking to recall something, modify or update some memory, or create a new one - you ALWAYS use your `memory_agent` (NOT `recall_agent_experiences`) to handle that request.
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
    tools=[get_current_datetime, AgentTool(create_vertex_search_agent())],
    sub_agents=[
        create_memory_agent(name="memory_agent", write="allowed", output_key=None),
        create_memory_agent(
            name="memory_agent_professional",
            instruction=create_read_instruction(MEMORY_TABLE) + WRITE_INSTRUCTION,
            write="allowed",
            output_key=None,
        ),
    ],
    before_agent_callback=[check_if_agent_should_run],
    # after_agent_callback=[memory_state_management],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)
    ),
)


root_agent = SequentialAgent(
    name="root_agent_flow",
    description="A sequence of agents utilizing a flow of converation supported by memories",
    sub_agents=[
        answer_validator_agent,
        memory_parallel_agent,
        summary_agent,
        main_agent,
    ],
)
