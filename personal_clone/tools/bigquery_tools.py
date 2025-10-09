from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode

import tempfile
from .. import config
import json
from google.oauth2 import service_account


def create_mel_bigquery_toolset():
    # bigquery_service_account_info = json.loads(config.MELL_GCP_SERVICE_ACCOUNT_INFO)

    # set google application credentials to use BigQuery tools
    mel_credentials = None
    if "mel_credentials" not in globals():
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_json:
            temp_json.write(config.MELL_GCP_SERVICE_ACCOUNT_INFO)
            temp_json.flush()
            MELL_GCP_SERVICE_ACCOUNT_INFO = json.load(open(temp_json.name))

        mel_credentials = service_account.Credentials.from_service_account_info(
            MELL_GCP_SERVICE_ACCOUNT_INFO
        )
    mel_credentials_config = BigQueryCredentialsConfig(credentials=mel_credentials)
    mel_tool_config = BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED, max_query_result_rows=10000
    )

    mel_bigquery_toolset = BigQueryToolset(
        credentials_config=mel_credentials_config, bigquery_tool_config=mel_tool_config
    )
    return mel_bigquery_toolset
