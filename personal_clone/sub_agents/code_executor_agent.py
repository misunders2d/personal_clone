from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor


def create_code_executor_agent(
    name: str = "code_executor_agent",
    instruction: str = "You are a simple code executor agent. You can execute small snippets of Python code.",
) -> Agent:
    graph_agent = Agent(
        name=name,
        description="""An agent that can execute Python code.""",
        instruction=instruction,
        model="gemini-2.5-flash",
        code_executor=BuiltInCodeExecutor(),
    )
    return graph_agent
