from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

dotenv_file_path = os.path.abspath(os.path.join(__file__, os.pardir, ".env"))
load_dotenv(dotenv_path=dotenv_file_path)

URI = os.environ.get("NEO4J_URI")
AUTH = (os.environ.get("NEO4J_USERNAME", ""), os.environ.get("NEO4J_PASSWORD", ""))
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


def execute_cypher_query(query: str, params: dict) -> dict:
    """
    Executes a Cypher query against the Neo4j graph knowledge database.

    For bulk operations, use a single query with the `UNWIND` clause and pass a list of objects as a parameter.
    This is more efficient than executing multiple queries.

    Example of UNWIND for bulk creation:
    Query:
        UNWIND $items AS item
        MERGE (n:MyNode {id: item.id})
        SET n += item
    Params:
        {'items': [{'id': 1, 'prop': 'A'}, {'id': 2, 'prop': 'B'}]}

    Args:
        query: The Cypher query to execute.
        params: A dictionary of parameters to pass to the query. May be an empty dict.

    Returns:
        A list of records, where each record is a dictionary representing a row in the result.
    """
    parameters = params or {}
    if not URI or not AUTH[0] or not AUTH[1]:
        raise ValueError(
            "Neo4j credentials (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD) are not set in the environment."
        )
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            driver.verify_connectivity()

            records, summary, _ = driver.execute_query(  # type: ignore
                query_=query,  # type: ignore
                parameters_=parameters,
                database_=NEO4J_DATABASE,
            )
            print(
                f"Query `{summary.query}` returned {len(records)} records in {summary.result_available_after} ms."
            )
        return {"status": "SUCCESS", "result": [record.data() for record in records]}
    except Exception as e:
        return {"status": "SUCCESS", "result": str(e)}
