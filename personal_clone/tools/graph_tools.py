from neo4j import GraphDatabase
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


from .. import config


def execute_cypher_query(
    query: str, params: dict
) -> dict:  # currently unused in favor of MCP toolset
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
    if not config.NEO4J_URI or not config.NEO4J_AUTH[0] or not config.NEO4J_AUTH[1]:
        raise ValueError(
            "Neo4j credentials (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD) are not set in the environment."
        )
    try:
        with GraphDatabase.driver(config.NEO4J_URI, auth=config.NEO4J_AUTH) as driver:
            driver.verify_connectivity()

            records, summary, _ = driver.execute_query(  # type: ignore
                query_=query,  # type: ignore
                parameters_=parameters,
                database_=config.NEO4J_DATABASE,
            )
            print(
                f"Query `{summary.query}` returned {len(records)} records in {summary.result_available_after} ms."
            )
        return {"status": "SUCCESS", "result": [record.data() for record in records]}
    except Exception as e:
        return {"status": "SUCCESS", "result": str(e)}


def create_neo4j_toolset():
    neo4j_toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@alanse/mcp-neo4j-server",
                ],
                env={
                    "NEO4J_URI": config.NEO4J_URI,
                    "NEO4J_USERNAME": config.NEO4J_AUTH[0],
                    "NEO4J_PASSWORD": config.NEO4J_AUTH[1],
                    "NEO4J_DATABASE": config.NEO4J_DATABASE,
                },
            ),
        ),
    )
    return neo4j_toolset
