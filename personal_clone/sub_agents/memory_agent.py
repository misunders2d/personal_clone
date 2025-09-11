from google.adk import Agent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from google.adk.planners import BuiltInPlanner
from google.genai import types
from typing import Literal

from ..callbacks.before_after_tool import memory_agent_tool_callback

from pydantic import BaseModel, Field

from google.oauth2 import service_account
import os
from dotenv import load_dotenv

dotenv_file_path = os.path.abspath(os.path.join(__file__, os.pardir, ".env"))
load_dotenv()
import json
import tempfile

with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_json:
    temp_json.write(os.environ["GCP_SERVICE_ACCOUNT_INFO"])
    temp_json.flush()
    GCP_SERVICE_ACCOUNT_INFO = json.load(open(temp_json.name))
DATASET_PATH = os.environ["MEMORY_DATASET_ID"]
MEMORY_TABLE = f"{DATASET_PATH}.memories"
PEOPLE_TABLE = f"{DATASET_PATH}.people"
EMBEDDING_MODEL = f"{DATASET_PATH}.embedding_model"
credentials = service_account.Credentials.from_service_account_info(
    GCP_SERVICE_ACCOUNT_INFO
)

READ_INSTRUCTION = f"""
    <GENERAL>
        You are an agent that can interact with specific tables in Google BigQuery to run SQL queries and manage memories and/or experiences.
        The main tables you are working with are `{MEMORY_TABLE}` and `{PEOPLE_TABLE}`.
        Memories are stored using vector embeddings, obtained from the model `{EMBEDDING_MODEL}`.

        Make sure to follow the output schema exactly if it's included.
    </GENERAL>

    <MEMORY MANAGEMENT WORKFLOW>
        0. FIRST, ALWAYS search the tables you have access to for the exact input the user has submitted. DON'T ASK ANY QUESTIONS.
        1. Understand the user's request and determine the appropriate SQL operation (SELECT, INSERT, UPDATE, DELETE).
        2. Inspect the schema of the `{MEMORY_TABLE}` table to understand its structure and columns. Pay attention to descriptions.
        3. Formulate the SQL query based on the user's request and the fields available in the table. Not all fields need to be used, but try to use as many as possible.
        4. Execute the SQL query using the BigQuery toolset's `execute_sql` function, do not use `ask_data_insights`:
            - For SELECT queries, retrieve the relevant memories and present them to the user. Use the query that user provided, do not come up with keywords. The vector search is a powerful tool that can search effectively by any queries.
            - For INSERT queries, add new memories to the table. Make sure to apply the logic from the example below to auto-generate the `memory_id`.
            - For UPDATE queries, modify existing memories as per the user's request. Do not overwrite the memory completely. Always make sure to update the `updated_at` field.
            - For DELETE queries, remove memories that are no longer needed. Confirm the user's intent before deletion.
        IMPORTANT: Always confirm the user's intent before performing any DELETE or UPDATE operations to avoid accidental data loss.
    </MEMORY MANAGEMENT WORKFLOW>
   
    <SPECIAL INSTRUCTIONS FOR RETRIEVING MEMORIES>
        When retrieving memories with a SELECT statement, you can try to use simple keyword matching on the `short_description`, `category`, `sentiment`, `tags`, and `source` fields to find relevant memories.
        However, for more complex queries that require semantic understanding, use vector similarity search on the `embedding` field.
        IMPORTANT! Always fetch the `memory_id`, `related_people` and `linked_memories` when doing the search and there are results.
        EXAMPLE - Use the following SQL expression to perform vector similarity search:
            ```
            WITH query_embedding AS (
            SELECT
                ml_generate_embedding_result AS embedding_vector
            FROM
                ML.GENERATE_EMBEDDING(
                MODEL `{EMBEDDING_MODEL}`,
                (SELECT '<user_query>' AS content),
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
                m.related_people,
                ML.DISTANCE(m.embedding, q.embedding_vector, 'COSINE') AS distance
            FROM
                `{MEMORY_TABLE}` AS m,
                query_embedding AS q
            )
            SELECT
            memory_id,
            full_content,
            short_description,
            category,
            sentiment,
            tags,
            related_people,
            distance
            FROM
            memories_with_distance
            ORDER BY
            distance ASC
            LIMIT 5
            ```
    </SPECIAL INSTRUCTIONS FOR RETRIEVING MEMORIES>
"""

WRITE_INSTRUCTION = f"""
    <SPECIAL INSTRUCTIONS FOR INSERTING NEW MEMORIES>
        When generating a new memory with an INSERT statement, the `memory_id` MUST be generated in the format 'mem_YYYY_MM_DD_xxxxxxxx' where YYYY is the year, MM is the month, DD is the day, and xxxxxxxx is a short unique identifier.
        All records in the table except `full_content` and `short_description` column MUST be in English. Make sure to translate any non-English tags, categories, sentiment etc. to English before inserting, and translate it back to the user's language when retrieving.
        Use the following SQL expression to generate the `memory_id`: `CONCAT('mem_', FORMAT_TIMESTAMP('%Y_%m_%d', CURRENT_TIMESTAMP()), '_', SUBSTR(GENERATE_UUID(), 1, 8))`
        Example:
            ```
                INSERT INTO `{MEMORY_TABLE}`
                (memory_id, user_id, full_content, short_description, embedding, category, sentiment, tags, source, style_influence, visibility, created_at, updated_at)
                WITH data_to_prepare AS (
                    SELECT
                        CONCAT('mem_', FORMAT_TIMESTAMP('%Y_%m_%d', CURRENT_TIMESTAMP()), '_', SUBSTR(GENERATE_UUID(), 1, 8)) AS memory_id,
                        'user@example.com' AS user_id,
                        'My cat Zephyr died last December.' AS full_content, -- Renamed from content
                        'Memory of Zephyr, a cat, who died last December.' AS short_description,
                        'personal' AS category,
                        'bad' AS sentiment,
                        ['cat', 'Zephyr', 'loss', 'December'] AS tags,
                        'chat' AS source,
                        TRUE AS style_influence,
                        'private' AS visibility,
                        CURRENT_TIMESTAMP() AS created_at,
                        CURRENT_TIMESTAMP() AS updated_at
                ),
                embedding_result AS (
                    SELECT
                        ml_generate_embedding_result AS embedding_vector
                    FROM
                        ML.GENERATE_EMBEDDING(
                            MODEL `{EMBEDDING_MODEL}`,
                            (SELECT short_description AS content FROM data_to_prepare), -- Input for embedding is short_description, aliased as content
                            STRUCT(TRUE AS flatten_json_output)
                        )
                )
                SELECT
                    dp.memory_id,
                    dp.user_id,
                    dp.full_content,
                    dp.short_description,
                    er.embedding_vector AS embedding,
                    dp.category,
                    dp.sentiment,
                    dp.tags,
                    dp.source,
                    dp.style_influence,
                    dp.visibility,
                    dp.created_at,
                    dp.updated_at
                FROM
                    data_to_prepare dp,
                    embedding_result er;
            ```
                **IMPORTANT:** If you are adding `linked_memories` field - make sure to update this field in the memory that you are linking to as well, to keep the relationship bidirectional.
    </SPECIAL INSTRUCTIONS FOR INSERTING NEW MEMORIES>

    <SPECIAL INSTRUCTIONS FOR UPDATING MEMORIES>
        - IMPORTANT! When updating memories with an UPDATE statement, **make sure to regenerate the embedding vectors** if tags or content is being changed.
        - ALWAYS announce the changes you've made to the user - including the embeddings regeneration.
        - Make sure NOT to delete the record completely, just modify the relevant information.
        - EXAMPLE:
        ```
            UPDATE `{MEMORY_TABLE}`
            SET
                full_content = 'My cat Zephyr died last December. This was a very sad event, and I miss him.', -- Update the main content
                short_description = 'Zephyr, my cat, died last December. This memory is about loss.', -- Update the short description
                embedding = (
                    SELECT
                        ml_generate_embedding_result
                    FROM
                        ML.GENERATE_EMBEDDING(
                            MODEL `{EMBEDDING_MODEL}`,
                            (SELECT 'Zephyr, my cat, died last December. This memory is about loss.' AS content), -- Embedding based on the new short_description
                            STRUCT(TRUE AS flatten_json_output)
                        )
                ),
                updated_at = CURRENT_TIMESTAMP()
            WHERE
                memory_id = 'your_memory_id';
        ```
    </SPECIAL INSTRUCTIONS FOR UPDATING MEMORIES>

    <PEOPLE DATA MANAGEMENT BEST PRACTICES>

        1.  **Always Check for Existing Records Before Creating:**
            *   **Purpose:** Prevent duplicate entries and maintain data integrity.
            *   **Method:** Before inserting a new person, perform a SELECT query on the people table using available identifiers (first name, last name, emails, Telegram handles, phone numbers). Check all relevant user_ids values.

        2.  **Understand the Table Schema:**
            *   **Purpose:** Ensure correct data types, required fields, and formatting.
            *   **Method:** Use get_table_info for the people table to review field names, types (e.g., STRING, REPEATED RECORD), and descriptions.

        3.  **Generate Unique `person_id`s:**
            *   **Purpose:** Provide a stable and unique identifier for each person.
            *   **Method:** For person_id, use the format CONCAT('per_', FORMAT_TIMESTAMP('%Y_%m_%d', CURRENT_TIMESTAMP()), '_', SUBSTR(GENERATE_UUID(), 1, 8)).

        4.  **Handle `user_ids` Correctly (Repeated Record):**
            *   **Purpose:** Store various contact details with clear identification of their type.
            *   **Method:** When inserting or updating, provide user_ids as an array of STRUCTs, each with an id_type (e.g., 'personal email', 'work email', 'telegram handle', 'phone number') and an id_value.

        5.  **Manage `relations` Bidirectionally (Repeated Record):**
            *   **Purpose:** Maintain consistent and accurate relationships between people.
            *   **Method:** When establishing a connection between two people:
                *   Retrieve current relations: Always fetch the existing relations array for both individuals.
                *   Append new relations: Use ARRAY_CONCAT to add new STRUCTs (containing related_person_id and relation_type) to the existing array.
                *   Update both records: Ensure the relationship is added to both individuals' relations fields.

        6.  **Always Update `updated_at` Timestamp:**
            *   **Purpose:** Track the last modification time for auditing and data freshness.
            *   **Method:** Include updated_at = CURRENT_TIMESTAMP() in every UPDATE statement.

        7.  **Integrate with `memories.related_people` (Special Handling):**
            *   **Context:** The related_people field in the memories table is a REPEATED STRING (stores names).
            *   **Method:**
                *   Add `person_id`: When linking a memory to a person from the people table, add their person_id (as a string) to the related_people array in the memories table using ARRAY_CONCAT.
                *   Remove Name String: Immediately after adding the person_id, remove the corresponding person's name string from the related_people array in that same memory record.

        8.  **Default `visibility` for New People:**
            *   **Purpose:** Streamline data entry based on user preference.
            *   **Method:** Unless otherwise specified, set the visibility for new people entries to 'public'.

        9.  **Clarify and Confirm:**
            *   **Purpose:** Ensure accurate data collection and prevent errors.
            *   **Method:** When information is missing or a request conflicts with schema definitions, ask clarifying questions. Confirm successful operations.        
    </PEOPLE DATA MANAGEMENT BEST PRACTICES>
"""


def create_bigquery_toolset(
    write: Literal["blocked", "allowed"] = "blocked",
) -> BigQueryToolset:
    write_mode = WriteMode.BLOCKED if write == "blocked" else WriteMode.ALLOWED
    tool_config = BigQueryToolConfig(write_mode=write_mode, max_query_result_rows=300)

    credentials_config = BigQueryCredentialsConfig(credentials=credentials)

    bigquery_toolset = BigQueryToolset(
        credentials_config=credentials_config, bigquery_tool_config=tool_config
    )
    return bigquery_toolset


class MemoryOutput(BaseModel):
    topic: str = Field(
        description="The main topic of the memory", examples=["`User's pet project`"]
    )
    content: str = Field(description="The actual contents of the memory or interaction")
    related_memories: list[str] = Field(
        description="List of related memories IDs from the `linked_memories` field, NOT general list of other memories in the table. Optional",
        examples=["mem_2025_09_05_2dba5961", "mem_2025_10_08_2ddas661"],
        default_factory=list,
    )
    related_people: list[str] = Field(
        description="List of related people IDS from the `related_people`. Optional",
        examples=["per_2025_09_05_26e44a10"],
        default_factory=list,
    )


def create_memory_agent(
    name: str = "memory_agent",
    write: Literal["blocked", "allowed"] = "allowed",
    instruction: str = READ_INSTRUCTION + WRITE_INSTRUCTION,
    output_schema: type[BaseModel] | None = None,
    output_key: str | None = None,
) -> Agent:
    memory_agent = Agent(
        name=name,
        description="""An agent that can handles experience and memory management - creating, retrieving, updating and deleting experiences or memories, based on its toolset.
            Use it whenever the conversation implies experience or memory management (remembering, recalling etc.).
            Also use it to manage people data in the people table.
            """,
        instruction=instruction,
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        ),
        tools=[create_bigquery_toolset(write=write)],
        output_schema=output_schema,
        # after_tool_callback=[memory_agent_tool_callback],
        output_key=output_key,
    )
    return memory_agent
