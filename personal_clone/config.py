from google.adk.planners import BuiltInPlanner, PlanReActPlanner
from google.genai import types

from google.adk.models.lite_llm import LiteLlm
from google.oauth2 import service_account
import google.auth
import os
import json
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
GOOGLE_CLOUD_STORAGE_BUCKET = os.environ["GOOGLE_CLOUD_STORAGE_BUCKET"]
VERTEX_DATASTORE_ID = os.environ["VERTEX_DATASTORE_ID"]
DATASTORE_ID = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/us/collections/default_collection/dataStores/{VERTEX_DATASTORE_ID}"
GCP_SERVICE_ACCOUNT_INFO = os.environ["GCP_SERVICE_ACCOUNT_INFO"]
MELL_GCP_SERVICE_ACCOUNT_INFO = os.environ["MELL_GCP_SERVICE_ACCOUNT_INFO"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GROK_API_KEY = os.environ["GROK_API_KEY"]

NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")
NEO4J_URI = os.environ.get("NEO4J_URI", "")
NEO4J_AUTH = (
    os.environ.get("NEO4J_USERNAME", ""),
    os.environ.get("NEO4J_PASSWORD", ""),
)

CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
CLICKUP_TEAM_ID = os.environ.get("CLICKUP_TEAM_ID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DEFAULT_GITHUB_REPO = os.environ.get("DEFAULT_GITHUB_REPO", "")

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")

DATASET_PATH = os.environ["MEMORY_DATASET_ID"]
MEMORY_TABLE = f"{DATASET_PATH}.memories_personal"
MEMORY_TABLE_PROFESSIONAL = f"{DATASET_PATH}.memories_professional"
PEOPLE_TABLE = f"{DATASET_PATH}.people"
MEMORY_CATEGORIES = {
    "idea": "New opportunities, proposals, brainstorms, pilots (not yet executed).",
    "memory": "Time-stamped events/decisions that record what happened (e.g., “we increased prices on X on Y”).",
    "knowledge": "Reference material, rules, pro-tips, or evergreen guidance (how-tos, best practices).",
    "procedure": "Step-by-step or operational playbooks (operational SOPs).",
    "experiment": "Tests/experimental runs with results and conclusions.",
    "incident": "Problems/complaints requiring follow up (IP theft, outages, bugs).",
    "project": "Initiatives, plans, or requests requiring work/tracking.",
    "technical": "Engineering or platform changes, debug notes, ML/SQL specifics.",
    "strategy": "High-level plans, promotional strategy, positioning (longer horizon).",
    "communication_style": "Templates / tone/style examples for messaging.",
    "policy": "sk — Policy issues or compliance / legal risks and guidance.",
    "operational": "Short operational updates (inventory, event-day notes) — for quick operational status.",
}
EMBEDDING_MODEL = f"{DATASET_PATH}.embedding_model"

SUPERUSERS = os.getenv("SUPERUSERS", "").split(",")
TEAM_DOMAIN = os.getenv("TEAM_DOMAIN", "")


# MODELS MANAGEMENT
def create_planner(mode: Literal["built-in", "react"] | None = None):
    if mode == "built-in":
        return BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        )
    elif mode == "react":
        return PlanReActPlanner()


# GROK MODELS
GROK_PRO_MODEL = LiteLlm(
    model="xai/grok-4-fast-reasoning", api_key=GROK_API_KEY
)  # 0.20 / 0.50
GROK_FLASH_MODEL = LiteLlm(
    model="xai/grok-4-fast-reasoning", api_key=GROK_API_KEY
)  # 0.20 / 0.50
GROK_LITE_MODEL = LiteLlm(
    model="xai/grok-4-fast-non-reasoning-latest", api_key=GROK_API_KEY
)  # 0.20 / 0.50

# OPENAI MODELS
OPENAI_PRO_MODEL = LiteLlm(model="openai/gpt-5", api_key=OPENAI_API_KEY)  # 1.25 / 10
OPENAI_FLASH_MODEL = LiteLlm(
    model="openai/gpt-5-mini", api_key=OPENAI_API_KEY
)  # 0.25 / 2.00
OPENAI_LITE_MODEL = LiteLlm(
    model="openai/gpt-5-nano", api_key=OPENAI_API_KEY
)  # 0.05 / 0.40

# GOOGLE MODLES
GOOGLE_PRO_MODEL = "gemini-2.5-pro"
GOOGLE_FLASH_MODEL = "gemini-2.5-flash"
GOOGLE_LITE_MODEL = "gemini-2.5-flash-lite"

GLOBAL_MODEL_PROVIDER: Literal["Google", "OpenAI", "Grok"] = "OpenAI"
GLOBAL_PLANNER = create_planner("built-in")

if GLOBAL_MODEL_PROVIDER == "Google":
    PRO_MODEL = GOOGLE_PRO_MODEL
    FLASH_MODEL = GOOGLE_FLASH_MODEL
    LITE_MODEL = GOOGLE_LITE_MODEL
elif GLOBAL_MODEL_PROVIDER == "OpenAI":
    PRO_MODEL = OPENAI_PRO_MODEL
    FLASH_MODEL = OPENAI_FLASH_MODEL
    LITE_MODEL = OPENAI_LITE_MODEL
elif GLOBAL_MODEL_PROVIDER == "Grok":
    PRO_MODEL = GROK_PRO_MODEL
    FLASH_MODEL = GROK_FLASH_MODEL
    LITE_MODEL = GROK_LITE_MODEL

# AGENT-SPECIFIC MODELS
ANSER_VALIDATOR_AGENT_MODEL = GOOGLE_LITE_MODEL

AGENT_MODEL = FLASH_MODEL
AGENT_PLANNER = GLOBAL_PLANNER

BIGQUERY_AGENT_MODEL = FLASH_MODEL
BIGQUERY_AGENT_PLANNER = GLOBAL_PLANNER

CLICKUP_AGENT_MODEL = FLASH_MODEL
CLICKUP_AGENT_PLANNER = GLOBAL_PLANNER

CODE_EXECUTOR_AGENT_MODEL = FLASH_MODEL
CODE_EXECUTOR_AGENT_PLANNER = GLOBAL_PLANNER

GITHUB_AGENT_MODEL = FLASH_MODEL
GITHUB_AGENT_PLANNER = GLOBAL_PLANNER

GOOGLE_SEARCH_AGENT_MODEL = GOOGLE_FLASH_MODEL
GOOGLE_SEARCH_AGENT_PLANNER = create_planner("built-in")

GRAPH_AGENT_MODEL = FLASH_MODEL
GRAPH_AGENT_PLANNER = GLOBAL_PLANNER

MEMORY_AGENT_MODEL = FLASH_MODEL
MEMORY_AGENT_PLANNER = GLOBAL_PLANNER

PINECONE_AGENT_MODEL = FLASH_MODEL
PINECONE_AGENT_PLANNER = GLOBAL_PLANNER

RAG_AGENT_MODEL = GOOGLE_FLASH_MODEL
RAG_AGENT_PLANNER = create_planner("built-in")

VERTEX_SEARCH_AGENT_MODEL = GOOGLE_LITE_MODEL
VERTEX_SEARCH_AGENT_PLANNER = None


# --- Auth ---
def get_identity_token(
    account: Literal[
        "GCP_SERVICE_ACCOUNT_INFO", "MELL_GCP_SERVICE_ACCOUNT_INFO"
    ] = "GCP_SERVICE_ACCOUNT_INFO",
):
    """Get identity token from the GCP service account string."""
    gcp_service_account_info_str = os.environ.get(account)
    if not gcp_service_account_info_str:
        raise ValueError(f"{account} environment variable not set.")

    service_info = json.loads(gcp_service_account_info_str)
    # project_id = service_info.get("project_id")

    credentials = service_account.Credentials.from_service_account_info(
        service_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    return credentials


if "credentials" not in globals():
    credentials = get_identity_token()
    google.auth.default = lambda *args, **kwargs: (credentials, credentials.project_id)
