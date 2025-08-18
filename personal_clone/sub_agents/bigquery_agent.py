from google.adk.agents import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.oauth2 import service_account
import tempfile

import os
import json

# Define a tool configuration to block any write operations
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

# Define a credentials config - in this example we are using application default
# credentials
# https://cloud.google.com/docs/authentication/provide-credentials-adc
# application_default_credentials, _ = google.auth.default()

try:
    import streamlit as st

    bigquery_service_account_info = st.secrets["BIGQUERY_SERVICE_ACCOUNT"]
    MODEL_NAME=st.secrets["MODEL_NAME"]
except:
    bigquery_service_account_info = json.loads(os.environ["BIGQUERY_SERVICE_ACCOUNT"])
    MODEL_NAME=os.environ["MODEL_NAME"]

with tempfile.NamedTemporaryFile(
    mode="w", delete=False, suffix=".json"
) as temp_key_file:
    json.dump(dict(bigquery_service_account_info), temp_key_file)
    temp_key_file_path = temp_key_file.name
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_file_path


credentials = service_account.Credentials.from_service_account_file(temp_key_file_path)


credentials_config = BigQueryCredentialsConfig(credentials=credentials)

# Instantiate a BigQuery toolset
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
)


# Agent Definition
def create_bigquery_agent():
    bigquery_agent = Agent(
        model=MODEL_NAME,
        name="bigquery_agent",
        description=(
            "Agent to answer questions about BigQuery data and models and execute"
            " SQL queries."
        ),
        instruction="""\
            You are a data science agent with access to several BigQuery tools.
            Make use of those tools to answer the user's questions.
            The main datasets you are working with are `mellanni-project-da.reports` and `mellanni-project-da.auxillary_development`.
            
            **IMPORTANT**
                The main mapping table for all products is `mellanni-project-da.auxillary_development.dictionary`
                *   This table contains the company's dictionary of all products, including their SKU, ASIN, and multiple parameters.
                *   When user asks about a "product" - they typically refer to the "Collection" column of this table.
                *   You **MUST** always include this table in your query if the user is interested in collection / product performance.

                Always check for duplicates.
                *   If you are planning to join the tables on specific columns, make sure the data in these columns is not duplicated.
                *   Duplicate values must be aggregated before joining to avoid data duplication.

                Marketplace / Country implication.
                *   If the user does not explicitly ask about a specific country, they always assume USA. Make sure to check relevant columns and their distinct values.

                Date and time
                *   If the user is asking for the "latest" or up-to-date data - make sure to identify and understand the "date"-related columns and use them in your queries.
        """,
        tools=[bigquery_toolset],
    )
    return bigquery_agent
