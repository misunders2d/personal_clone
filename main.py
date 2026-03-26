import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv, set_key
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from personal_clone.app_utils.config_manager import ALLOWED_CONFIG_KEYS, update_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Metadata for every configurable key — drives the setup wizard UI
CONFIG_FIELDS = [
    {
        "key": "GEMINI_API_KEY",
        "label": "Google Gemini API Key",
        "section": "required",
        "type": "password",
        "placeholder": "AIzaSy...",
        "help": "Powers the agent brain. Get one free at https://aistudio.google.com/app/apikey",
    },
    {
        "key": "TELEGRAM_BOT_TOKEN",
        "label": "Telegram Bot Token",
        "section": "messaging",
        "type": "password",
        "placeholder": "123456:ABC-DEF...",
        "help": "Create a bot via @BotFather on Telegram, copy the token it gives you.",
    },
    {
        "key": "TELEGRAM_WEBHOOK_SECRET",
        "label": "Telegram Webhook Secret",
        "section": "messaging",
        "type": "password",
        "placeholder": "(optional — leave empty to use polling mode)",
        "help": "Only needed for webhook mode. Leave empty to use automatic polling (no public URL required).",
    },
    {
        "key": "SLACK_BOT_TOKEN",
        "label": "Slack Bot Token",
        "section": "messaging",
        "type": "password",
        "placeholder": "xoxb-...",
        "help": "Create a Slack App, add bot scopes, install to workspace, then copy the Bot User OAuth Token.",
    },
    {
        "key": "SLACK_APP_TOKEN",
        "label": "Slack App Token",
        "section": "messaging",
        "type": "password",
        "placeholder": "xapp-...",
        "help": "Found in App Settings -> Basic Information -> App-Level Tokens.",
    },
    {
        "key": "SLACK_SIGNING_SECRET",
        "label": "Slack Signing Secret",
        "section": "messaging",
        "type": "password",
        "placeholder": "abc123def456...",
        "help": "Found on your Slack App's Basic Information page under App Credentials.",
    },
    {
        "key": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "section": "optional_models",
        "type": "password",
        "placeholder": "sk-...",
        "help": "Optional: Use GPT models via LiteLLM.",
    },
    {
        "key": "CLAUDE_API_KEY",
        "label": "Claude API Key",
        "section": "optional_models",
        "type": "password",
        "placeholder": "sk-ant-...",
        "help": "Optional: Use Claude models via LiteLLM.",
    },
    {
        "key": "PINECONE_API_KEY",
        "label": "Pinecone API Key",
        "section": "memory",
        "type": "password",
        "placeholder": "pinecone-...",
        "help": "For long-term memory. Get one at https://app.pinecone.io/",
    },
    {
        "key": "PINECONE_INDEX_NAME",
        "label": "Pinecone Index Name",
        "section": "memory",
        "type": "text",
        "placeholder": "personal-clone",
        "help": "The name of your Pinecone index.",
    },
    {
        "key": "CLICKUP_API_TOKEN",
        "label": "ClickUp API Token",
        "section": "integrations",
        "type": "password",
        "placeholder": "pk_...",
        "help": "For task management. Get one in ClickUp settings.",
    },
    {
        "key": "CLICKUP_TEAM_ID",
        "label": "ClickUp Team ID",
        "section": "integrations",
        "type": "text",
        "placeholder": "12345678",
        "help": "Your ClickUp workspace/team ID.",
    },
    {
        "key": "GITHUB_TOKEN",
        "label": "GitHub Personal Access Token",
        "section": "evolution",
        "type": "password",
        "placeholder": "ghp_...",
        "help": "For the self-evolution feature. Generate at github.com/settings/tokens with 'repo' scope.",
    },
    {
        "key": "DEFAULT_GITHUB_REPO",
        "label": "GitHub Repository",
        "section": "evolution",
        "type": "text",
        "placeholder": "your-username/personal-clone",
        "help": "Format: owner/repo. The repository the agent pushes improvements to.",
    },
    {
        "key": "BQ_GCP_SERVICE_ACCOUNT_INFO",
        "label": "BigQuery Service Account (JSON)",
        "section": "advanced",
        "type": "textarea",
        "placeholder": '{"type": "service_account", ...}',
        "help": "Advanced: Paste the entire JSON content of your Google Cloud service account key for BigQuery access.",
    },
]

# Load environment variables on startup
ENV_FILE_PATH = os.environ.get("DOTENV_PATH", "./data/.env")
os.makedirs(os.path.dirname(ENV_FILE_PATH), exist_ok=True)
if os.path.exists(ENV_FILE_PATH):
    load_dotenv(ENV_FILE_PATH, override=True)

# Generate or load a persistent ADMIN_PASSCODE for the web wizard
ADMIN_PASSCODE = os.environ.get("ADMIN_PASSCODE")
_first_boot = False
if not ADMIN_PASSCODE:
    _first_boot = True
    ADMIN_PASSCODE = secrets.token_hex(16).upper()
    set_key(ENV_FILE_PATH, "ADMIN_PASSCODE", ADMIN_PASSCODE)
    os.environ["ADMIN_PASSCODE"] = ADMIN_PASSCODE

status = "READY" if os.environ.get("GEMINI_API_KEY") else "UNCONFIGURED"

print("\n" + "=" * 60)
print("  PERSONAL CLONE AGENT")
print(f"  Management Portal: http://localhost:8081/setup")
print(f"  Status:            [{status}]")
if _first_boot:
    print()
    print(f"  Your Admin Passcode: {ADMIN_PASSCODE}")
    print()
    print("  SAVE THIS PASSCODE — you need it to access the Setup Wizard.")
    print(f"  It is also stored in: {ENV_FILE_PATH}")
else:
    print(f"  Admin Passcode:    stored in {ENV_FILE_PATH}")
print("=" * 60 + "\n")

# CSRF token store (session-based CSRF tokens for /setup)
_csrf_tokens: dict[str, float] = {}
CSRF_TOKEN_TTL = 3600  # 1 hour

_poller_task = None
_slack_task = None


def _generate_csrf_token() -> str:
    """Generate a CSRF token and store it with a timestamp."""
    token = secrets.token_hex(32)
    # Evict expired tokens
    now = time.time()
    expired = [t for t, ts in _csrf_tokens.items() if now - ts > CSRF_TOKEN_TTL]
    for t in expired:
        _csrf_tokens.pop(t, None)
    _csrf_tokens[token] = now
    return token


def _validate_csrf_token(token: str) -> bool:
    """Validate and consume a CSRF token."""
    ts = _csrf_tokens.pop(token, None)
    if ts is None:
        return False
    return (time.time() - ts) < CSRF_TOKEN_TTL


def _start_telegram_poller():
    """Start (or restart) the Telegram poller background task."""
    global _poller_task
    from personal_clone.telegram_poller import poll_telegram
    # Cancel existing poller if running
    if _poller_task and not _poller_task.done():
        _poller_task.cancel()
    _poller_task = asyncio.create_task(
        poll_telegram(get_runner, process_init_command)
    )


def _start_slack_handler():
    """Start (or restart) the Slack socket mode handler."""
    global _slack_task
    from personal_clone.slack_app import run_slack_forever
    if _slack_task and not _slack_task.done():
        _slack_task.cancel()
    _slack_task = asyncio.create_task(
        run_slack_forever(process_init_command)
    )


def get_runner():
    """Proxy to the lazy runner initializer."""
    from personal_clone.app_utils.agent_runner import get_runner as _get_runner
    return _get_runner()


def process_init_command(text: str) -> str:
    """Handle /init commands — update config, reset runner, restart pollers."""
    result = update_config(text, admin_passcode=ADMIN_PASSCODE)
    if "updated" in result.lower():
        from personal_clone.app_utils.agent_runner import reload_runner
        reload_runner()
        _start_telegram_poller()
        _start_slack_handler()
    return result


def _build_setup_context(request: Request, **extra):
    """Build the full template context for the setup wizard."""
    def mask(key):
        val = os.environ.get(key, "")
        if len(val) > 8:
            return f"{val[:4]}...{val[-4:]}"
        return "Configured" if val else ""

    fields = []
    for f in CONFIG_FIELDS:
        fields.append({**f, "current": mask(f["key"]), "connected": bool(os.environ.get(f["key"]))})

    sections = {
        "required": [f for f in fields if f["section"] == "required"],
        "messaging": [f for f in fields if f["section"] == "messaging"],
        "optional_models": [f for f in fields if f["section"] == "optional_models"],
        "memory": [f for f in fields if f["section"] == "memory"],
        "integrations": [f for f in fields if f["section"] == "integrations"],
        "evolution": [f for f in fields if f["section"] == "evolution"],
        "advanced": [f for f in fields if f["section"] == "advanced"],
    }

    core_ready = bool(os.environ.get("GEMINI_API_KEY"))
    messaging_ready = bool(os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN"))

    return {
        "request": request,
        "sections": sections,
        "fields": fields,
        "config": {f["key"]: mask(f["key"]) for f in CONFIG_FIELDS},
        "core_ready": core_ready,
        "messaging_ready": messaging_ready,
        "csrf_token": _generate_csrf_token(),
        "app_name": "Personal Clone",
        "success": False,
        **extra,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    from personal_clone.app_utils.scheduler_instance import scheduler
    logger.info("Starting Personal Clone lifecycle...")

    scheduler.start()
    logger.info("Scheduler started.")

    _start_telegram_poller()
    _start_slack_handler()

    yield

    # Shutdown
    logger.info("Stopping Personal Clone lifecycle...")
    if _poller_task and not _poller_task.done():
        _poller_task.cancel()
        try:
            await _poller_task
        except asyncio.CancelledError:
            pass
    if _slack_task and not _slack_task.done():
        _slack_task.cancel()
        try:
            await _slack_task
        except asyncio.CancelledError:
            pass
    scheduler.shutdown()
    logger.info("Scheduler stopped.")


# Initialize FastAPI
fastapi_app = FastAPI(title="Personal Clone Agent", lifespan=lifespan)
templates = Jinja2Templates(directory="personal_clone/templates")


# Setup Wizard UI Routes
@fastapi_app.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request):
    return templates.TemplateResponse("setup.html", _build_setup_context(request))


@fastapi_app.post("/setup", response_class=HTMLResponse)
async def setup_post(request: Request):
    form_data = await request.form()
    passcode = form_data.get("admin_passcode", "")
    csrf_token = form_data.get("csrf_token", "")

    if not _validate_csrf_token(csrf_token):
        return templates.TemplateResponse("setup.html", _build_setup_context(
            request, error="Invalid or expired form submission. Please try again."
        ))

    if not passcode or not hmac.compare_digest(passcode, ADMIN_PASSCODE):
        return templates.TemplateResponse("setup.html", _build_setup_context(
            request, error="Invalid Admin Passcode."
        ))

    updated = []
    for field in CONFIG_FIELDS:
        key = field["key"]
        value = form_data.get(key, form_data.get(key.lower(), "")).strip()
        if value and key in ALLOWED_CONFIG_KEYS:
            # Don't overwrite with masked placeholders
            if "..." in value and len(value) < 20:
                continue
            set_key(ENV_FILE_PATH, key, value)
            os.environ[key] = value
            updated.append(field["label"])

    # Reset runner and restart pollers if anything changed
    if updated:
        from personal_clone.app_utils.agent_runner import reload_runner
        reload_runner()
        _start_telegram_poller()
        _start_slack_handler()

    ctx = _build_setup_context(request, success=True)
    if updated:
        ctx["updated_keys"] = updated
    return templates.TemplateResponse("setup.html", ctx)


@fastapi_app.get("/health")
def health_check():
    configured = {k for k in ALLOWED_CONFIG_KEYS if os.environ.get(k)}
    core_ready = bool(os.environ.get("GEMINI_API_KEY"))
    messaging_ready = bool(
        os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
    )
    return {
        "status": "ready" if core_ready else "unconfigured",
        "core_ready": core_ready,
        "messaging_ready": messaging_ready,
        "integrations": {
            k: ("connected" if os.environ.get(k) else "missing")
            for k in sorted(ALLOWED_CONFIG_KEYS)
        },
    }


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(fastapi_app, host=host, port=port)
