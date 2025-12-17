from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from .. import config


def create_code_executor_agent(
    name: str = "code_executor_agent",
    instruction: str = "You are a simple code executor agent. You can execute small snippets of Python code.",
) -> Agent:
    graph_agent = Agent(
        name=name,
        description="""An agent that can execute Python code.""",
        instruction=instruction,
        model=config.CODE_EXECUTOR_AGENT_MODEL,
        code_executor=BuiltInCodeExecutor(),
        planner=config.CODE_EXECUTOR_AGENT_PLANNER,
    )
    return graph_agent
