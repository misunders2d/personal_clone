import asyncio
import logging
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from ..agent import get_app

logger = logging.getLogger(__name__)

_runner_instance = None

def get_runner():
    """Lazily initialize and return the ADK Runner instance."""
    global _runner_instance
    if _runner_instance is None:
        try:
            app_instance = get_app()
            # Use SQLite for persistent sessions
            session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///./data/personal_clone.db")
            _runner_instance = Runner(
                agent=app_instance.root_agent,
                app_name="personal_clone",
                session_service=session_service,
            )
            logger.info("ADK Runner initialized.")
        except Exception:
            logger.exception("Failed to initialize ADK Runner")
            return None
    return _runner_instance

def reload_runner():
    """Forces the runner to be re-initialized on next call (useful after config change)."""
    global _runner_instance
    _runner_instance = None
    logger.info("ADK Runner flagged for reload.")
