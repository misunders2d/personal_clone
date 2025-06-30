from google.adk import Agent
from .search import write_to_rag, read_from_rag

master_agent = Agent(
    name = "personal_clone",
    description = """A personal clone agent that can answer questions about your life, work, and experiences.
    It can also write new experiences to your personal knowledge base.""",
    model='gemini-2.5-flash',
    tools = [write_to_rag, read_from_rag],
)

root_agent = master_agent