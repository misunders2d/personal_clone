from google.adk import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.planners import BuiltInPlanner
from google.genai import types

from google.oauth2 import service_account
import os
import json

GCP_SERVICE_ACCOUNT_INFO = json.loads(os.environ['GCP_SERVICE_ACCOUNT_INFO'])
MEMORY_TABLE = os.environ['MEMORY_TABLE_ID']
DATASET_PATH = MEMORY_TABLE.split('.')[:-1]
EMBEDDING_MODEL = '.'.join(DATASET_PATH + ['embedding_model'])
credentials = service_account.Credentials.from_service_account_info(GCP_SERVICE_ACCOUNT_INFO)

tool_config = BigQueryToolConfig(write_mode=WriteMode.ALLOWED, max_query_result_rows=100)

credentials_config = BigQueryCredentialsConfig(credentials=credentials)

bigquery_toolset = BigQueryToolset(credentials_config=credentials_config, bigquery_tool_config=tool_config)


memory_agent = Agent(
    name='memory_agent',
    description='An agent that can handles memory management - creating, retrieving, updating and deleting memories.',
    instruction=f"""You are an agent that can interact with a specific table in Google BigQuery to run SQL queries and manage memories.
    The main table you are working with is `{MEMORY_TABLE}`.
    Memories are stored using vector embeddings, obtained from the model `{EMBEDDING_MODEL}`.

    ***MEMORY MANAGEMENT WORKFLOW***
    1. Understand the user's request and determine the appropriate SQL operation (SELECT, INSERT, UPDATE, DELETE).
    2. Inspect the schema of the `{MEMORY_TABLE}` table to understand its structure and columns. Pay attention to descriptions.
    3. Formulate the SQL query based on the user's request and the fields available in the table. Not all fields need to be used, but try to use as many as possible.
    4. Execute the SQL query using the BigQuery toolset's `execute_sql` function, do not use `ask_data_insights`:
         - For SELECT queries, retrieve the relevant memories and present them to the user.
         - For INSERT queries, add new memories to the table. Make sure to apply the logic from the example below to auto-generate the `memory_id`.
         - For UPDATE queries, modify existing memories as per the user's request. Always make sure to update the `updated_at` field.
         - For DELETE queries, remove memories that are no longer needed. Confirm the user's intent before deletion.
    IMPORTANT: Always confirm the user's intent before performing any DELETE or UPDATE operations to avoid accidental data loss.

    ***SPECIAL INSTRUCTIONS FOR INSERTING NEW MEMORIES***
    When generating a new memory with an INSERT statement, the `memory_id` MUST be generated in the format 'mem_YYYY_MM_DD_xxxxxxxx' where YYYY is the year, MM is the month, DD is the day, and xxxxxxxx is a short unique identifier.
    Use the following SQL expression to generate the `memory_id`: `CONCAT('mem_', FORMAT_TIMESTAMP('%Y_%m_%d', CURRENT_TIMESTAMP()), '_', SUBSTR(GENERATE_UUID(), 1, 8))`
    Example:
        ```
            INSERT INTO `{MEMORY_TABLE}`
            (memory_id, user_id, content, embedding, category, sentiment, tags, source, style_influence, visibility, created_at, updated_at)
            WITH emb AS (
            SELECT
                CONCAT('mem_', FORMAT_TIMESTAMP('%Y_%m_%d', CURRENT_TIMESTAMP()), '_', SUBSTR(GENERATE_UUID(), 1, 8)) AS memory_id,
                'me' AS user_id,
                'My cat Zephyr died last December.' AS content,
                ml_generate_embedding_result AS embedding,
                'personal' AS category,
                'bad' AS sentiment,
                ['cat', 'Zephyr', 'loss', 'December'] AS tags,
                'chat' AS source,
                TRUE AS style_influence,
                'private' AS visibility,
                CURRENT_TIMESTAMP() AS created_at,
                CURRENT_TIMESTAMP() AS updated_at
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{EMBEDDING_MODEL}`,
                (SELECT 'My cat Zephyr died last December.' AS content),
                STRUCT(TRUE AS flatten_json_output)
            )
            )
            SELECT * FROM emb;
        ```

    """,
    model='gemini-2.5-flash',
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)),
    tools=[bigquery_toolset],
)