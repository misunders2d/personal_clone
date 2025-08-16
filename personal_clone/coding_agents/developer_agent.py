from google.adk.agents import Agent, LoopAgent, SequentialAgent
from google.adk.tools import exit_loop, AgentTool
from google.adk.tools.load_web_page import load_web_page
from google.adk.models.lite_llm import LiteLlm
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.planners import BuiltInPlanner

from google.genai import types

import os

from ..sub_agents.search_agent import create_search_agent_tool


from ..utils.github_utils import create_github_toolset

from .. import instructions

import os

MODEL_NAME = os.environ["MODEL_NAME"]


def create_code_inspector_agent(name="code_inspector_agent"):
    inspector_agent = Agent(
        name=name,
        model=MODEL_NAME,
        code_executor=BuiltInCodeExecutor(),
        instruction=instructions.CODE_INSPECTOR_AGENT_INSTRUCTION,
        description="A sandboxed agent that executes Python code snippets for introspection and verification.",
    )
    return inspector_agent


def create_planner_agent():
    planner_agent = Agent(
        name=f"planner_agent",
        description="Creates and refines development plans.",
        instruction=instructions.PLANNER_AGENT_INSTRUCTION,
        model=MODEL_NAME,
        tools=[
            create_search_agent_tool(),
            AgentTool(agent=create_code_inspector_agent()),
            create_github_toolset(),
            exit_loop,
            load_web_page,
        ],
        output_key="development_plan",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=2048
            )
        ),
    )
    return planner_agent


def create_code_reviewer_agent():
    code_reviewer_agent = Agent(
        name="code_reviewer_agent",
        description="Reviews development plans for quality and adherence to project standards.",
        instruction=instructions.CODE_REVIEWER_AGENT_INSTRUCTION,
        model=LiteLlm(os.environ["DEVELOPER_AGENT_MODEL"]),
        tools=[
            create_github_toolset(),
            create_search_agent_tool(),
            AgentTool(
                agent=create_code_inspector_agent(
                    name="code_inspector_for_reviewer_agent"
                )
            ),
            load_web_page,
        ],
        output_key="reviewer_feedback",
    )
    return code_reviewer_agent


def create_plan_fetcher_agent():
    plan_fetcher_agent = Agent(
        name="plan_fetcher_agent",
        description="Fetches development plan from session state.",
        instruction="""
Your only job is to fetch the approved development plan(s) from {development_plan}.
IMPORTANT! DO NOT MODIFY THE PLAN IN ANY WAY. OUTPUT IT UNCHANGED!
""",
        model=MODEL_NAME,
        tools=[],
    )
    return plan_fetcher_agent


# Loop and sequence creation


def create_code_review_loop():
    code_review_loop = LoopAgent(
        name=f"review_loop",
        description="A loop agent that creates and reviews development plans iteratively to achieve best results.",
        sub_agents=[create_planner_agent(), create_code_reviewer_agent()],
        max_iterations=int(os.environ["MAX_LOOP_ITERATIONS"]),
    )
    return code_review_loop


def plan_and_review_agent():
    plan_and_review_agent = SequentialAgent(
        name="plan_and_review_agent",
        description="An agent that runs code planning and review processes and outputs streamlined plans",
        sub_agents=[create_code_review_loop(), create_plan_fetcher_agent()],
    )
    return plan_and_review_agent


# master developer creation


def create_developer_agent():
    developer_agent = Agent(
        name="developer_agent",
        description="A developer agent that can plan and execute code changes after user approval.",
        instruction=instructions.DEVELOPER_AGENT_INSTRUCTION,
        model=MODEL_NAME,
        sub_agents=[plan_and_review_agent()],
        tools=[create_github_toolset()],
    )
    return developer_agent
