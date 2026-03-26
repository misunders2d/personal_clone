import logging
import os

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

logger = logging.getLogger(__name__)

_runner_instance = None


def get_runner():
    """Lazily initialize and return the ADK Runner instance."""
    global _runner_instance
    if _runner_instance is not None:
        return _runner_instance

    # Guard: don't attempt init without the core API key
    if not os.environ.get("GEMINI_API_KEY"):
        return None

    try:
        # Import inside function to prevent module-level crashes
        # when GEMINI_API_KEY is missing during first boot.
        from ..agent import get_app

        app_instance = get_app()

        db_path = os.path.abspath("./data/personal_clone.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        database_url = f"sqlite+aiosqlite:///{db_path}"
        session_service = DatabaseSessionService(db_url=database_url)

        _runner_instance = Runner(
            agent=app_instance.root_agent,
            app_name=app_instance.name,
            session_service=session_service,
        )
        logger.info("ADK Runner initialized.")
        return _runner_instance
    except Exception:
        logger.exception("Failed to initialize ADK Runner")
        return None


def reload_runner():
    """Forces the runner to be re-initialized on next call (useful after config change)."""
    global _runner_instance
    _runner_instance = None
    logger.info("ADK Runner flagged for reload.")
