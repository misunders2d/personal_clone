# from google.adk.tools.bigquery import BigQueryCredentialsConfig
# from google.adk.tools.bigquery import BigQueryToolset
# from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

# from google.cloud import bigquery

# import json
# import tempfile
# from google.oauth2 import service_account

# from .. import config

# credentials = None


# def get_credentials():
#     global credentials
#     with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_json:
#         temp_json.write(config.GCP_SERVICE_ACCOUNT_INFO)
#         temp_json.flush()
#         GCP_SERVICE_ACCOUNT_INFO = json.load(open(temp_json.name))

#     credentials = service_account.Credentials.from_service_account_info(
#         GCP_SERVICE_ACCOUNT_INFO
#     )
#     return credentials


# if not credentials:
#     credentials = get_credentials()


# def create_bigquery_toolset():

#     tool_config = BigQueryToolConfig(
#         write_mode=WriteMode.ALLOWED, max_query_result_rows=300
#     )

#     credentials_config = BigQueryCredentialsConfig(credentials=credentials)

#     bigquery_toolset = BigQueryToolset(
#         credentials_config=credentials_config, bigquery_tool_config=tool_config
#     )
#     return bigquery_toolset


# def search_bq(table: str, text_to_search: str) -> dict:
#     """A hardcoded function to perform pre-agent run BigQuery search to supply context"""
#     text_to_search = text_to_search.strip()
#     data = {}
#     query = f"""
#         WITH query_embedding AS (
#             SELECT
#                 ml_generate_embedding_result AS embedding_vector
#             FROM
#                 ML.GENERATE_EMBEDDING(
#                 MODEL `{config.EMBEDDING_MODEL}`,
#                 (SELECT "{text_to_search}" AS content),
#                 STRUCT(TRUE AS flatten_json_output)
#                 )
#             ),
#             memories_with_distance AS (
#             SELECT
#                 m.memory_id,
#                 m.full_content,
#                 m.short_description,
#                 m.category,
#                 m.sentiment,
#                 m.tags,
#                 m.linked_memories,
#                 m.related_people,
#                 ML.DISTANCE(m.embedding, q.embedding_vector, 'COSINE') AS distance
#             FROM
#                 `{table}` AS m,
#                 query_embedding AS q
#             )
#             SELECT
#                 memory_id,
#                 full_content,
#                 short_description,
#                 category,
#                 sentiment,
#                 tags,
#                 linked_memories,
#                 related_people,
#                 distance
#             FROM
#                 memories_with_distance
#             WHERE
#                 distance < 0.5
#             ORDER BY
#                 distance ASC
#             LIMIT 15

#     """
#     try:
#         if credentials:
#             with bigquery.Client(
#                 credentials=credentials, project=credentials.project_id
#             ) as client:
#                 result = client.query(query)
#                 for row in result.result():
#                     data[row[0]] = {
#                         "full_content": row[1],
#                         "short_description": row[2],
#                         "category": row[3],
#                         "sentiment": row[4],
#                         "tags": row[5],
#                         "linked_memories": row[6],
#                         "related_people": row[7],
#                     }
#         return data
#     except Exception as e:
#         return {"status": "FAILED", "error": str(e)}


# def search_people(query: str) -> dict:
#     """A hardcoded function to perform pre-agent run BigQuery people search to supply context"""
#     data = {}
#     try:
#         credentials = get_credentials()
#         with bigquery.Client(
#             credentials=credentials, project=credentials.project_id
#         ) as client:
#             result = client.query(query)
#             for row in result.result():
#                 data[row[0]] = {
#                     "first_name": row[1],
#                     "last_name": row[2],
#                     "role": row[3],
#                 }
#         return data
#     except Exception as e:
#         return {"status": "FAILED", "error": str(e)}


# def search_user_id(memory_id: list | str) -> dict:
#     query = f"SELECT memory_id, user_id FROM {config.MEMORY_TABLE_PROFESSIONAL} WHERE "
#     if isinstance(memory_id, str):
#         query += f"""memory_id = "{memory_id}" """
#     elif isinstance(memory_id, list):
#         memory_id_list = '","'.join(memory_id)
#         query += f"""memory_id in ("{memory_id_list}")"""
#     data = {}
#     try:
#         if credentials:
#             with bigquery.Client(
#                 credentials=credentials, project=credentials.project_id
#             ) as client:
#                 result = client.query(query)
#                 for row in result.result():
#                     data[row[0]] = row[1]
#         return data
#     except Exception as e:
#         return {"status": "FAILED", "error": str(e)}


# def is_read_only(query) -> dict:
#     try:
#         if credentials:
#             job_config = bigquery.QueryJobConfig(dry_run=True)
#             with bigquery.Client(
#                 credentials=credentials, project=credentials.project_id
#             ) as client:
#                 dry_run_job = client.query(query, job_config=job_config)
#             return {
#                 "status": "success",
#                 "result": (dry_run_job.statement_type == "SELECT"),
#             }
#         else:
#             return {"status": "success", "result": False}
#     except Exception as e:
#         return {"status": "error", "result": str(e)}
