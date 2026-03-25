import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv, set_key
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

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
        "placeholder": "{\"type\": \"service_account\", ...}",
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
print(f"  Management Portal: http://localhost:8080/setup")
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

def generate_csrf_token():
    token = secrets.token_hex(16)
    _csrf_tokens[token] = time.time() + CSRF_TOKEN_TTL
    return token

def validate_csrf_token(token: str):
    expiry = _csrf_tokens.get(token)
    if not expiry or time.time() > expiry:
        return False
    # Use and discard (one-time use tokens)
    del _csrf_tokens[token]
    return True

from personal_clone.app_utils.scheduler_instance import scheduler

_poller_task = None
_slack_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poller_task, _slack_task
    # This runs on startup
    logger.info("Starting Personal Clone lifecycle...")

    # Start the task scheduler
    scheduler.start()
    logger.info("Scheduler started.")

    # Start Telegram poller
    from personal_clone.telegram_poller import poll_telegram
    _poller_task = asyncio.create_task(
        poll_telegram(lambda text: update_config(text, ADMIN_PASSCODE))
    )

    # Start Slack handler
    from personal_clone.slack_app import run_slack_forever
    _slack_task = asyncio.create_task(run_slack_forever())

    yield

    # This runs on shutdown
    logger.info("Stopping Personal Clone lifecycle...")
    if _poller_task:
        _poller_task.cancel()
    if _slack_task:
        _slack_task.cancel()
    scheduler.shutdown()
    logger.info("Scheduler stopped.")

# Initialize FastAPI
fastapi_app = FastAPI(title="Personal Clone Agent", lifespan=lifespan)
templates = Jinja2Templates(directory="personal_clone/templates")

# Setup Wizard UI Routes
@fastapi_app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    csrf_token = generate_csrf_token()
    current_config = {key: os.environ.get(key, "") for key in ALLOWED_CONFIG_KEYS}
    
    # Mask passwords
    for field in CONFIG_FIELDS:
        key = field["key"]
        if field["type"] == "password" and current_config.get(key):
            val = current_config[key]
            current_config[key] = val[:4] + "*" * (len(val)-8) + val[-4:] if len(val) > 8 else "****"

    return templates.TemplateResponse(
        "setup.html", 
        {
            "request": request, 
            "fields": CONFIG_FIELDS, 
            "config": current_config,
            "csrf_token": csrf_token,
            "app_name": "Personal Clone"
        }
    )

@fastapi_app.post("/setup", response_class=HTMLResponse)
async def handle_setup(request: Request):
    form_data = await request.form()
    
    # Check admin passcode
    passcode = form_data.get("admin_passcode")
    if not hmac.compare_digest(passcode or "", ADMIN_PASSCODE):
        return HTMLResponse("Unauthorized: Invalid Admin Passcode", status_code=401)
    
    # Validate CSRF
    if not validate_csrf_token(form_data.get("csrf_token", "")):
        return HTMLResponse("Invalid CSRF token", status_code=400)

    # Filter and update keys
    update_str = ""
    for key in ALLOWED_CONFIG_KEYS:
        if key in form_data:
            val = form_data[key].strip()
            # Don't overwrite with masked placeholders
            if val and not (val.startswith("****") or ("***" in val and len(val) < 20)):
                update_str += f" {key}={val}"

    if update_str:
        result = update_config(f"/init {ADMIN_PASSCODE} {update_str}", ADMIN_PASSCODE)
        logger.info(f"Config Update: {result}")

    return HTMLResponse("<script>alert('Configuration saved! The server will now reload.'); window.location.href='/setup';</script>")

@fastapi_app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    # Default to 127.0.0.1 for local safety, but allow 0.0.0.0 for Docker
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(fastapi_app, host=host, port=port)
