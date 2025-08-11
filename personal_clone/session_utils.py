import json
from google.adk.runners import Runner

def get_session_events_as_json() -> str:
    """
    Retrieves the events of the current session and returns them as a JSON string.

    Returns:
        A JSON string representing the session events.
    """
    try:
        # This is a long shot, but we'll try to find the runner in the global context.
        runner_instance = None
        for obj in globals().values():
            if isinstance(obj, Runner):
                runner_instance = obj
                break

        if not runner_instance:
            return json.dumps([{"error": "Runner instance not found."}])

        session = runner_instance.session
        if not session:
            return json.dumps([{"error": "Session not found in runner."}])

        events = []
        if hasattr(session, 'events') and session.events:
            for event in session.events:
                if hasattr(event, 'to_dict'):
                    events.append(event.to_dict())
                elif hasattr(event, '__dict__'):
                    events.append(event.__dict__)
                else:
                    pass
        
        return json.dumps(events, indent=2)

    except Exception as e:
        return json.dumps([{"error": f"Could not retrieve session events: {str(e)}"}])