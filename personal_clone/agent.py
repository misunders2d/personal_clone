from google.adk.agents import Agent, SequentialAgent  # , ParallelAgent

# from google.adk. models.lite_llm import LiteLlm
from google.adk.tools import AgentTool
from google.adk.planners import BuiltInPlanner
from google.genai import types
from pydantic import BaseModel, Field


from .sub_agents.code_executor_agent import create_code_executor_agent
from .sub_agents.memory_agent import (
    create_memory_agent,
    create_memory_agent_instruction,
)
from .sub_agents.vertex_search_agent import create_vertex_search_agent
from .sub_agents.graph_agent import create_graph_agent
from .sub_agents.google_search_agent import create_google_search_agent
from .callbacks.before_after_agent import (
    check_if_agent_should_run,
    state_setter,
    prefetch_memories,
)

from .tools.web_search_tools import scrape_web_page
from .tools.datetime_tools import get_current_datetime

from . import config


class ValidatorOutput(BaseModel):
    answer_needed: bool = Field(
        default=True,
        description="True or False depending on whether the anser is required or implied. Default to True if you have any doubts",
    )
    rr: bool = Field(
        default=False,
        description="True or False depending on whether memory search should be involved",
    )


def create_answer_validator_agent():
    answer_validator_agent = Agent(
        name="answer_validator_agent",
        description="Checks the user input and decides whether or not the user's question actually requires a response",
        model="gemini-2.0-flash",
        instruction="""You are an agent designed to assess the user's input.
        You need to evaluate TWO parameters:
            - `answer_needed`: whether or not the `personal_clone` agent should reply to the user's query.
                If the {user_id} starts with "GMAIL:" - you MUST reply with `True`.
                Sometimes the user's resonse does not require an answer, like "okay", "bye" etc.
                HOWEVER if the user is explicilty demanding an answer or if the user is asking a question, you ALWAYS reply with `True`.
                The ONLY scenario when you reply with `False` is when the user's input is a simple acknowledgement, farewell, or similar non-inquisitive statement.
                If the user's input looks like a command or a request for action, you MUST reply with `True`.
                If the user's reply looks like a confirmation for the agent's actions (like "good to go", "yes", "confirmed" etc), you MUST reply with `True`.
                If the user's input ends with a question mark, you MUST reply with `True`. If you are in doubt - MUST defer to `True`.
                In general - unless you are absolutely sure the user's input does not require an answer, you output `True`.
            - `rr`: whether or not a memory seach should be involved.
                If the user's query or the conversational flow implies that there is some memory or experience involved, you should set the `memory_search_needed` to `True`, otherwise set it to `False`.

        You do not output anything except `True` or `False` for each of those fields.
        """,
        output_key="answer_validation",
        before_agent_callback=[state_setter],
        after_agent_callback=[prefetch_memories],
        output_schema=ValidatorOutput,
    )
    return answer_validator_agent


def create_main_agent():
    main_agent = Agent(
        model="gemini-2.5-flash",
        # model  = LiteLlm(model="openai/gpt-4.1"),
        name="personal_clone",
        description="A helpful assistant for user questions.",
        instruction="""
        <GENERAL>
            - You are an assistant, a secretary and a second brain for the person whose ID is one of {master_user_id}.
            - The current date and time are store in {current_datetime} key.
            - You learn from the communication with this user, copy their style.
            - At the same time you are an employee of Mellanni company, and you are being addressed by multiple co-workers in multiple conversational environments - Slack, Gmail, Google Meet etc.
            - You are equipped with different sub-agents and tools that help you manage the conversation. Specific tools are used to store and retrieve memories and experiences - use them widely.
            - Your `memory_agent` has access to all personal experiences, and your `memory_agent_professional` has access to all professional experiences. Use them accordingly.
        </GENERAL>
        <CONVERSATION FLOW>
            - You are participating both in one-on-one chats with just one user AND in group/channel chats with multiple users.
            - For convenience the currently active user id is stored in {user_id} key, and all user-related information is stored in {user_related_context} key.
            - If there is no data in {user_related_context}, you should politely ask this user to introduce themselves and store that data in the people table.
            - When addressed, you not only reply to the user's query, but also assess the conversational context and offer help, solutions or suggestions proactively. Use all available tools to make the life of the user easier.
            - **Act as a 'True Thinker': Do not simply regurgitate stored information. Instead, actively integrate all relevant knowledge from your personal and professional memories, leverage your full Google search capabilities for comprehensive research, and engage in an iterative, multi-turn dialogue as needed to fully understand problems, synthesize insights, and drive towards actionable solutions or a complete understanding of the user's objectives.
            Your overall tone is informal and concise, unless explicitly specified otherwise.
        </CONVERSATION FLOW>
        <IMPORTANT!>
            <MEMORY USAGE>
                - You DISREGARD all outputs of the `answer_validator_agent`, this is a technical routing agent not intended for user or agent interaction.
                - You are equipped with a system of agents who fetch knowledge and memories based on the user's input BEFORE you start your communication.
                    Before you utilize your memory agents, refer to {memory_context}, {memory_context_professional} and {vertex_context} to make your conversation as context-aware, as possible.
                    Don't use memory agents if there is enough information in the session state, or unless the user expicitly asks to use memory tools or agents.
                - If the information in the state is not enough or if the user is explicitly asking to recall something, modify or update some memory, or create a new one - you ALWAYS use your memory agents to handle that request.
            </MEMORY USAGE>
            <ERROR HANDLING>
                - If you receive an error message from any of the tools or sub-agents - you MUST follow the <MEMORY USAGE> protocol. Only if such an error is not found in memories, should you seek guidance from the user.
                - After the issue has been successfully resolved - you MUST use the `memory_agent` to remember (save) this experience, so that you can refer to it later.
            </ERROR HANDLING>
            <GOOGLE SEARCH>
                - You have access to the `google_search_agent` who can perform Google searches to find relevant information on the web.
                - Apart from the summary, the agent stores the full text and grounding metadata (including links) in {google_search_grounding} key.
                    Use this information to support the agent's answers with links, and also to be able to use your `scrape_web_page` tool to extract more information from the linked pages, if needed.
            </GOOGLE SEARCH>
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
        tools=[
            get_current_datetime,
            AgentTool(create_vertex_search_agent()),
            AgentTool(create_code_executor_agent()),
            AgentTool(create_google_search_agent()),
            scrape_web_page,
        ],
        sub_agents=[
            create_memory_agent(
                scope="personal",
                name="memory_agent",
                instruction=create_memory_agent_instruction(table=config.MEMORY_TABLE),
                output_key="memory_search",
            ),
            create_memory_agent(
                scope="professional",
                name="memory_agent_professional",
                instruction=create_memory_agent_instruction(
                    config.MEMORY_TABLE_PROFESSIONAL
                ),
                output_key="memory_search_professional",
            ),
            create_graph_agent(),
        ],
        before_agent_callback=[check_if_agent_should_run],  # prefetch_memories],
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        ),
    )
    return main_agent


root_agent = SequentialAgent(
    name="root_agent_flow",
    description="A sequence of agents utilizing a flow of converation supported by memories",
    sub_agents=[
        create_answer_validator_agent(),
        # memory_parallel_agent,
        create_main_agent(),
    ],
)
