from google.adk.agents import Agent

def get_current_datetime():
    from datetime import datetime
    return datetime.now().isoformat()

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[get_current_datetime]
)
