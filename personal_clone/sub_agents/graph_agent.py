from google.adk import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

from ..tools.graph_tools import execute_cypher_query

import os
from dotenv import load_dotenv

dotenv_file_path = os.path.abspath(os.path.join(__file__, os.pardir, ".env"))
load_dotenv(dotenv_path=dotenv_file_path)

NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE")


def create_graph_agent_instruction():
    return f"""
    <GENERAL>
        You are an agent that interacts with a Neo4j graph database to manage a knowledge graph of entities and their relationships.
        You will use the `execute_cypher_query` tool to run Cypher queries.
        The database you are working with is `{NEO4J_DATABASE}`.

        Make sure to follow the output schema exactly if it's included.
    </GENERAL>

    <SPECIAL INSTRUCTIONS FOR DATA MODEL>
        - Entities are represented as nodes with labels (e.g., `:Person`, `:Location`, `:Concept`).
        - Nodes should have a `name` property that is unique for that entity type.
        - Relationships are represented by directed edges with types (e.g., `-[:KNOWS]->`, `-[:LOCATED_IN]->`).
        - Use `MERGE` to create or find nodes and relationships to avoid duplicates. ALWAYS use `MERGE` on the `name` property.
    </SPECIAL INSTRUCTIONS FOR DATA MODEL>

    <SPECIAL INSTRUCTIONS FOR RETRIEVING DATA>
        - Use `MATCH` clauses to specify patterns to search for.
        - For semantic or similarity-based searches, you can use vector indexes if they exist. Assume an index named `knowledge-graph-embeddings` exists on nodes.
        - EXAMPLE - Vector similarity search for a concept:

            ```cypher
            CALL db.index.vector.queryNodes('knowledge-graph-embeddings', 10, $embedding) YIELD node, score
            RETURN node.name, node.description, score
            ```
        - When returning data, always include identifiers like the node name or other unique properties.
    </SPECIAL INSTRUCTIONS FOR RETRIEVING DATA>

    <SPECIAL INSTRUCTIONS FOR INSERTING/UPDATING DATA>
        - Use `MERGE` to create a node or relationship only if it doesn't already exist. This is critical for data integrity.
        - Use `ON CREATE SET` to set properties when a new node/relationship is created.
        - Use `ON MATCH SET` to update properties if the node/relationship already exists.
        - **For bulk operations (creating or updating multiple nodes or relationships at once), use the `UNWIND` clause with a list of parameters. This is much more efficient than running multiple queries.**
        - EXAMPLE - Creating a person and connecting them to a location:

            ```cypher
            MERGE (p:Person {{name: $person_name}})
            ON CREATE SET p.created_at = timestamp()
            MERGE (l:Location {{name: $location_name}})
            ON CREATE SET l.created_at = timestamp()
            MERGE (p)-[r:LIVES_IN]->(l)
            ON CREATE SET r.since = $year
            ```
        - **EXAMPLE - Bulk creating people using `UNWIND`:**

            ```cypher
            UNWIND $people_data AS person_props
            MERGE (p:Person {{name: person_props.name}})
            ON CREATE SET p.created_at = timestamp()
            SET p += person_props
            ```
            *In this case, the `params` argument for `execute_cypher_query` would be `{{'people_data': [{{'name': 'Alice', 'age': 31}}, {{'name': 'Bob', 'age': 32}}]}}`.*
    </SPECIAL INSTRUCTIONS FOR INSERTING/UPDATING DATA>

    <KNOWLEDGE GRAPH MANAGEMENT WORKFLOW>
        0. FIRST, analyze the user's request to understand what entities and relationships are involved.
        1. Determine the appropriate Cypher operation (`MATCH` for reading, `MERGE` for writing/updating).
        2. Formulate the Cypher query based on the user's request and the data modeling best practices.
        3. Execute the query using the `execute_cypher_query` tool. Provide parameters separately.
        4. Analyze the results from the tool and present them to the user in a clear, human-readable format.
        5. If the user asks to delete information, use a `MATCH` query to find the node, and then `DETACH DELETE` to remove it and its relationships. ALWAYS confirm with the user before deleting.
    </KNOWLEDGE GRAPH MANAGEMENT WORKFLOW>
"""


def create_graph_agent(
    name: str = "graph_agent",
    instruction: str = create_graph_agent_instruction(),
) -> Agent:
    graph_agent = Agent(
        name=name,
        description="""An agent that manages a knowledge graph in a Neo4j database. It can create, retrieve, update, and delete entities and their relationships using Cypher queries. Use it for any tasks involving structured knowledge, relationships between concepts, or graph-based data analysis.""",
        instruction=instruction,
        model="gemini-2.5-flash",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=-1
            )
        ),
        tools=[execute_cypher_query],
    )
    return graph_agent
