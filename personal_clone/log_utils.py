from google.adk.tools.tool_context import ToolContext
from google.adk.sessions import Session

def get_session(tool_context: ToolContext) -> Session:
    """
    Retrieves the current session object.

    Args:
        tool_context (ToolContext): The context object containing the session.

    Returns:
        The Session object.
    """
    if not tool_context:
        raise ValueError("Tool context not found.")

    invocation_context = getattr(tool_context, '_invocation_context', None)
    if not invocation_context:
        raise ValueError("Invocation context not found in tool_context.")

    session = getattr(invocation_context, 'session', None)
    if not session:
        raise ValueError("Session not found in invocation_context.")

    return session
