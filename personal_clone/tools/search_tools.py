from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

from google.cloud import bigquery

import json
import tempfile
from google.oauth2 import service_account

from .. import config

with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_json:
    temp_json.write(config.GCP_SERVICE_ACCOUNT_INFO)
    temp_json.flush()
    GCP_SERVICE_ACCOUNT_INFO = json.load(open(temp_json.name))

credentials = service_account.Credentials.from_service_account_info(
    GCP_SERVICE_ACCOUNT_INFO
)

tool_config = BigQueryToolConfig(
    write_mode=WriteMode.ALLOWED, max_query_result_rows=300
)

credentials_config = BigQueryCredentialsConfig(credentials=credentials)

bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
)


def search_bq(table: str, text_to_search: str) -> dict:
    """A hardcoded function to perform pre-agent run BigQuery search to supply context"""
    text_to_search = text_to_search.strip()
    data = {}
    try:
        client = bigquery.Client(
            credentials=credentials, project=credentials.project_id
        )
        query = f"""
            WITH query_embedding AS (
                SELECT
                    ml_generate_embedding_result AS embedding_vector
                FROM
                    ML.GENERATE_EMBEDDING(
                    MODEL `{config.EMBEDDING_MODEL}`,
                    (SELECT "{text_to_search}" AS content),
                    STRUCT(TRUE AS flatten_json_output)
                    )
                ),
                memories_with_distance AS (
                SELECT
                    m.memory_id,
                    m.full_content,
                    m.short_description,
                    m.category,
                    m.sentiment,
                    m.tags,
                    m.linked_memories,
                    m.related_people,
                    ML.DISTANCE(m.embedding, q.embedding_vector, 'COSINE') AS distance
                FROM
                    `{table}` AS m,
                    query_embedding AS q
                )
                SELECT
                    memory_id,
                    full_content,
                    short_description,
                    category,
                    sentiment,
                    tags,
                    linked_memories,
                    related_people,
                    distance
                FROM
                    memories_with_distance
                WHERE
                    distance < 0.5
                ORDER BY
                    distance ASC
                LIMIT 15    

        """
        result = client.query(query)
        for row in result.result():
            data[row[0]] = {
                "full_content": row[1],
                "short_description": row[2],
                "category": row[3],
                "sentiment": row[4],
                "tags": row[5],
                "linked_memories": row[6],
                "related_people": row[7],
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
    return data


def search_people(query: str) -> dict:
    """A hardcoded function to perform pre-agent run BigQuery people search to supply context"""
    data = {}
    try:
        client = bigquery.Client(
            credentials=credentials, project=credentials.project_id
        )
        result = client.query(query)
        for row in result.result():
            data[row[0]] = {
                "first_name": row[1],
                "last_name": row[2],
                "role": row[3],
            }
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
    return data
