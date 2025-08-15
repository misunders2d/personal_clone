from adk.tools import Tool, toolset

def my_example_tool_function(name: str):
    """
    A simple example tool function.
    """
    return f"Hello, {name}! This is an example from my_toolset.py"

my_example_tool = Tool(
    name="my_example_tool",
    description="An example tool to say hello.",
    parameters=[
        {"name": "name", "type": "str", "description": "The name to greet."}
    ],
    function=my_example_tool_function,
)

my_tool_set = toolset(
    name="MyExampleToolset",
    tools=[my_example_tool],
)
