from google.adk.models.lite_llm import LiteLlm
from google.oauth2 import service_account
import google.auth
import os
import json
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
VERTEX_DATASTORE_ID = os.environ["VERTEX_DATASTORE_ID"]
DATASTORE_ID = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/global/collections/default_collection/dataStores/{VERTEX_DATASTORE_ID}"

GCP_SERVICE_ACCOUNT_INFO = os.environ["GCP_SERVICE_ACCOUNT_INFO"]
MELL_GCP_SERVICE_ACCOUNT_INFO = os.environ["MELL_GCP_SERVICE_ACCOUNT_INFO"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")
URI = os.environ.get("NEO4J_URI")
AUTH = (os.environ.get("NEO4J_USERNAME", ""), os.environ.get("NEO4J_PASSWORD", ""))

CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DEFAULT_GITHUB_REPO = os.environ.get("DEFAULT_GITHUB_REPO", "")

DATASET_PATH = os.environ["MEMORY_DATASET_ID"]
MEMORY_TABLE = f"{DATASET_PATH}.memories_personal"
MEMORY_TABLE_PROFESSIONAL = f"{DATASET_PATH}.memories_professional"
PEOPLE_TABLE = f"{DATASET_PATH}.people"
EMBEDDING_MODEL = f"{DATASET_PATH}.embedding_model"


SUPERUSERS = os.getenv("SUPERUSERS", "").split(",")
TEAM_DOMAIN = os.getenv("TEAM_DOMAIN", "")

# MODELS MANAGEMENT
GLOBAL_MODEL_PROVIDER = "OpenAI"
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

if GLOBAL_MODEL_PROVIDER == "Google":
    PRO_MODEL = GOOGLE_PRO_MODEL
    FLASH_MODEL = GOOGLE_FLASH_MODEL
    LITE_MODEL = GOOGLE_LITE_MODEL
elif GLOBAL_MODEL_PROVIDER == "OpenAI":
    PRO_MODEL = OPENAI_PRO_MODEL
    FLASH_MODEL = OPENAI_FLASH_MODEL
    LITE_MODEL = OPENAI_LITE_MODEL


# --- Auth ---
def get_identity_token():
    """Get identity token from the GCP service account string."""
    gcp_service_account_info_str = os.environ.get("GCP_SERVICE_ACCOUNT_INFO")
    if not gcp_service_account_info_str:
        raise ValueError("GCP_SERVICE_ACCOUNT_INFO environment variable not set.")

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
