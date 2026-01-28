from google.adk.agents import Agent, SequentialAgent  # , ParallelAgent
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig

# from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.plugins import ReflectAndRetryToolPlugin

# from google.adk.tools.load_memory_tool import load_memory_tool
# from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.adk.tools.agent_tool import AgentTool
from pydantic import BaseModel, Field

# from .tools.github_tools import create_adk_docs_mcp_toolset
from . import config

# from .sub_agents.pinecone_agent import create_pinecone_agent
from .callbacks.before_after_agent import (
    check_if_agent_should_run,
    prefetch_memories,
    state_setter,
)

# from .callbacks.before_after_tool import on_tool_error_callback

from .sub_agents.bigquery_agent import create_bigquery_agent
from .sub_agents.clickup_agent import create_clickup_agent
from .sub_agents.code_executor_agent import create_code_executor_agent
from .sub_agents.github_agent import create_github_agent

# from .sub_agents.rag_agent import create_rag_agent
# from .sub_agents.graph_agent import create_graph_agent
from .sub_agents.google_search_agent import create_google_search_agent
from .sub_agents.memory_agent import create_memory_agent
from .sub_agents.vertex_search_agent import create_vertex_search_agent
from .tools.datetime_tools import get_current_datetime
from .tools.session_state_tools import delete_goals, set_goals, query_session_state
from .tools.web_search_tools import scrape_web_page
from .tools.youtube_tools import youtube_summary


class ValidatorOutput(BaseModel):
    reply: bool = Field(
        default=True,
        description="True or False depending on whether the answer is required or implied. Default to True if you have any doubts",
    )
    recall: bool = Field(
        default=False,
        description="True or False depending on whether memory search should be involved",
    )
    reasoning: bool = Field(
        default=False,
        description="True or False depending on whether or not an agent should activate reasoning/deeper thinking",
    )


def create_answer_validator_agent():
    answer_validator_agent = Agent(
        name="answer_validator_agent",
        description="Checks the user input and decides whether or not the user's question actually requires a response",
        model=config.ANSWER_VALIDATOR_AGENT_MODEL,
        instruction="""You are an agent designed to assess the user's input.
        You need to evaluate TWO parameters:
            - `reply`: whether or not the `personal_clone` agent should reply to the user's query.
                If the {user_id} starts with "GMAIL:" - you MUST reply with `True`.
                Sometimes the user's response does not require an answer, like "okay", "bye" etc.
                HOWEVER if the user is explicitly demanding an answer or if the user is asking a question, you ALWAYS reply with `True`.
                The ONLY scenario when you reply with `False` is when the user's input is a simple acknowledgement, farewell, or similar non-inquisitive statement.
                If the user's input looks like a command or a request for action, you MUST reply with `True`.
                If the user's reply looks like a confirmation for the agent's actions (like "good to go", "yes", "confirmed" etc), you MUST reply with `True`.
                If the user's input ends with a question mark, you MUST reply with `True`. If you are in doubt - MUST defer to `True`.
                In general - unless you are absolutely sure the user's input does not require an answer, you output `True`.
            - `recall`: whether or not a memory search should be involved.
                If the user's query or the conversational flow implies that there is some memory or experience involved, you should set the `recall` to `True`, otherwise set it to `False`.
            - `reasoning`: whether or not an agent should use Planner/Reasoning mode.
                If the user's query or the conversational flow implies that there is a need of a longer thinking or deep research (complex questions, multi-step procedures, etc.) or the use explicitly asks to think deeper, do a research or plan, you should set the `reasoning` to `True`, otherwise set it to `False`.

        You do not output anything except `True` or `False` for each of those fields.
        """,
        output_key="answer_validation",
        before_agent_callback=[state_setter],
        after_agent_callback=[prefetch_memories],
        output_schema=ValidatorOutput,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
    return answer_validator_agent


def create_main_agent():
    main_agent_toolset = [
        # load_memory_tool,
        # preload_memory_tool,
        get_current_datetime,
        AgentTool(create_code_executor_agent()),
        AgentTool(create_google_search_agent()),
        scrape_web_page,
        set_goals,
        delete_goals,
        query_session_state,
        youtube_summary,
    ]

    main_agent = Agent(
        model=config.AGENT_MODEL,
        name="personal_clone",
        description="A helpful assistant for user questions.",
        instruction="""
        <GENERAL>
            - You are "Bezos", a male assistant, secretary, and second brain for {master_user_id}.
            - Current date and time: {current_datetime}.
            - You represent Mellanni company in Slack, Gmail, Google Meet, etc.
            - Equiped with specialized sub-agents and tools (including GitHub, ClickUp, BigQuery, and Google Search). ALWAYS query sub-agents for their latest capabilities.
            - You have access to three primary knowledge layers:
                1. SESSION STATE (Short-term): Use `set_goals`, `delete_goals`, `query_session_state`. Non-persistent tasks/reminders.
                2. MEMORY AGENT (Long-term): Uses Pinecone for personal/professional experiences. Persistent and modifiable.
                3. VERTEX SEARCH (Internal Docs): Immutable company SOPs, documents, and data via `vertex_search_agent`.
            - Use the `True_Thinker` algorithm for complex problem-solving or multi-step reasoning.
        </GENERAL>

        <COMMUNICATION_GUIDELINES>
            - Tone: Casual, concise, non-AI. Use contractions and colloquialisms.
            - Style: Short, chat-friendly answers. Stylistic errors/incomplete sentences are fine.
            - Language: Reply in the user's language.
            - Constraint: Do not overpromise. Do not suggest actions you cannot perform.
            - Proactivity: Assess context and offer solutions proactively.
            - Follow-ups: Only ask clarifying questions if the request is genuinely ambiguous (per `True_Thinker`). Avoid generic "How can I help more?" questions.
        </COMMUNICATION_GUIDELINES>

        <SPECIALIZED_TASKS>
            <SHORT_TERM_GOALS>
                Manage tasks/reminders per user ({user_id}) using `set_goals` and `delete_goals`. Always confirm storage to the user.
            </SHORT_TERM_GOALS>
            <GITHUB_DEVELOPMENT>
                Use `github_agent` for all code-related changes. It handles feature branches, commits, and PRs safely. Never merge to master yourself.
            </GITHUB_DEVELOPMENT>
            <PROJECT_MANAGEMENT>
                Use `clickup_agent` to manage tasks and retrieval from ClickUp.
            </PROJECT_MANAGEMENT>
            <BUSINESS_ANALYTICS>
                Use `bigquery_agent` for sales, inventory, and business performance queries.
            </BUSINESS_ANALYTICS>
            <AMAZON_SELLER_CENTRAL>
                For Amazon-related questions, scrape and refer to: `https://sellercentral.amazon.com/help/hub/reference/external/G2`. Provide direct links.
            </AMAZON_SELLER_CENTRAL>
        </SPECIALIZED_TASKS>

        <CORE_LOGIC>
            <ALGORITHM NAME="True_Thinker">
                <PHASE NAME="Deconstruction_and_Clarification">
                    <STEP NAME="Initial_Parsing">Identify core components and desired outcome.</STEP>
                    <STEP NAME="Ambiguity_Check">If the request is unclear, DO NOT make assumptions. Ask targeted clarifications (max 2 attempts).</STEP>
                    <STEP NAME="Clarification_Safety">If ambiguity remains after 2 attempts, proceed with the best interpretation, marking it as a low-confidence assumption.</STEP>
                </PHASE>
                <PHASE NAME="Information_Gathering_and_Analysis">
                    <STEP NAME="Strategic_Querying">Assess and execute queries against Vertex (SOPs), BigQuery (Data), Web, or Memory.</STEP>
                </PHASE>
                <PHASE NAME="Synthesis_and_Solution">
                    <STEP NAME="Recursive_Check">Retry once if gaps or contradictions are found. Escalate if still unresolved.</STEP>
                    <STEP NAME="Confidence_Scoring">Assign scores (0.0-1.0). Threshold for auto-execution: 0.8.</STEP>
                    <STEP NAME="Problem_Reframing">If the stated problem is just a symptom, reframe and seek approval before proceeding (unless confidence > 0.9).</STEP>
                </PHASE>
                <PHASE NAME="Delivery_and_Learning">
                    <STEP NAME="Structured_Response">Present solution with confidence score and assumptions.</STEP>
                    <STEP NAME="Outcome_Recording">Log interaction to BigQuery via the memory layers for future reference.</STEP>
                </PHASE>
            </ALGORITHM>
        </CORE_LOGIC>

        <IMPORTANT_REPRESENTATION>
            <MEMORY_CONTEXT>
                - Refer to {memory_context}, {memory_context_professional}, {rag_context}, and {vertex_context} BEFORE using memory tools.
                - Use `memory_agent` primarily when state info is insufficient or explicit recall/update is requested.
            </MEMORY_CONTEXT>
            <ERROR_HANDLING>
                - On tool/agent error: Consult memories for historical fixes FIRST. Seek user help only as a last resort.
                - Post-resolution: Use `True_Thinker`'s learning phase to save the experience.
            </ERROR_HANDLING>
            <WEB_RESEARCH>
                - `Google Search_agent` summary and grounding metadata (links) are in {google_search_grounding}.
                - Support answers with links; use `scrape_web_page` for deep dives.
            </WEB_RESEARCH>
        </IMPORTANT_REPRESENTATION>

        """,
        tools=main_agent_toolset,
        sub_agents=[
            create_memory_agent(),
            create_bigquery_agent(),
            create_clickup_agent(),
            create_github_agent(),
            create_vertex_search_agent(),
        ],
        before_agent_callback=[check_if_agent_should_run],
        # on_tool_error_callback=on_tool_error_callback,
        planner=config.AGENT_PLANNER,
    )
    return main_agent


root_agent = SequentialAgent(
    name="root_agent_flow",
    description="A sequence of agents utilizing a flow of conversation supported by memories",
    sub_agents=[
        create_answer_validator_agent(),
        create_main_agent(),
    ],
)

app = App(
    name="personal_clone",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,
        overlap_size=2,
        # summarizer=LlmEventSummarizer(llm=config.FLASH_MODEL),
    ),
    context_cache_config=ContextCacheConfig(
        cache_intervals=20, ttl_seconds=1800, min_tokens=32000
    ),
    plugins=[ReflectAndRetryToolPlugin(max_retries=3)],
)
