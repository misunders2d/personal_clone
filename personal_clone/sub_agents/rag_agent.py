# Efficient but expensive service, use for enterprise-level data

from vertexai import rag
import vertexai
from google.adk import Agent
import re

from .. import config

from ..callbacks.before_after_tool import before_rag_edit_callback

vertexai.init(
    project=config.GOOGLE_CLOUD_PROJECT,
    location=config.GOOGLE_CLOUD_LOCATION,
    # credentials=rag_credentials
)  # location needs to be set to "us-east4" until there's enough quota on "us-central1"


def create_corpus(display_name: str) -> dict:
    """Creates a RagCorpus if it does not already exist.
    Args:
        display_name: The meaningful display name of the corpus to create.
    Returns: A dict with the status of the operation and corpus details.
    """
    try:
        embedding_model_config = rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model="publishers/google/models/text-embedding-005"
            )
        )

        rag_corpus = rag.create_corpus(
            display_name=display_name,
            backend_config=rag.RagVectorDbConfig(
                rag_embedding_model_config=embedding_model_config
            ),
        )
        return {
            "status": "created",
            "rag_corpus_name": rag_corpus.name,
            "display_name": rag_corpus.display_name,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def upload_files_to_corpus(corpus_name: str, paths: list[str]) -> dict:
    """Uploads files to a RagCorpus.

    Args:
        corpus_name: The name of the corpus to upload files to. Make sure to use FULL name, not the display name.
        paths: A list of paths to files or directories to upload. Supports Google Cloud Storage and Google Drive Links.
    Returns: A dict with the status of the operation.
    """
    validated_paths = []
    invalid_paths = []
    conversions = []

    for path in paths:
        if not path or not isinstance(path, str):
            invalid_paths.append(f"{path} (Not a valid string)")
            continue

        docs_match = re.match(
            r"https:\/\/docs\.google\.com\/(?:document|spreadsheets|presentation)\/d\/([a-zA-Z0-9_-]+)(?:\/|$)",
            path,
        )
        if docs_match:
            file_id = docs_match.group(1)
            drive_url = f"https://drive.google.com/file/d/{file_id}/view"
            validated_paths.append(drive_url)
            conversions.append(f"{path} → {drive_url}")
            continue

        drive_match = re.match(
            r"https:\/\/drive\.google\.com\/(?:file\/d\/|open\?id=)([a-zA-Z0-9_-]+)(?:\/|$)",
            path,
        )
        if drive_match:
            file_id = drive_match.group(1)
            drive_url = f"https://drive.google.com/file/d/{file_id}/view"
            validated_paths.append(drive_url)
            if drive_url != path:
                conversions.append(f"{path} → {drive_url}")
            continue

        if path.startswith("gs://"):
            validated_paths.append(path)
            continue

        invalid_paths.append(f"{path} (Invalid format)")

    if not validated_paths:
        return {
            "status": "error",
            "message": "No valid paths provided. Please provide Google Drive URLs or GCS paths.",
            "corpus_name": corpus_name,
            "invalid_paths": invalid_paths,
        }

    try:
        rag.import_files(
            corpus_name,
            validated_paths,
            transformation_config=rag.TransformationConfig(
                chunking_config=rag.ChunkingConfig(
                    chunk_size=512,
                    chunk_overlap=100,
                ),
            ),
            max_embedding_requests_per_min=1000,  # Optional
        )
        return {"status": "upload_started", "corpus_name": corpus_name, "paths": paths}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def delete_files_from_corpus(corpus_name: str, file_ids: list[str]) -> dict:
    """Deletes files from a RagCorpus.

    Args:
        corpus_name: The name of the corpus to delete files from.
        file_ids: A list of file IDs to delete. Obtainable from `rag.list_files()`.
    Returns: A dict with the status of the operation.
    """
    successful_deletions = []
    failed_deletions = []
    for file_id in file_ids:
        try:
            rag.delete_file(
                corpus_name,
                file_id,
            )
            successful_deletions.append(file_id)
        except Exception as e:
            failed_deletions.append({"file_id": file_id, "error": str(e)})

    return {
        "status": "completed",
        "deleted_file_ids": file_ids,
        "failed_deletions": failed_deletions,
    }


def delete_corpus(corpus_name: str) -> dict:
    """Deletes a RagCorpus.

    Args:
        corpus_name: The name of the corpus to delete.
    Returns: A dict with the status of the operation.
    """
    try:
        rag.delete_corpus(corpus_name)
        return {"status": "deleted", "corpus_name": corpus_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_corpora() -> list[dict]:
    """Lists all RagCorpora in the project.

    Returns: A list of dicts with corpus details.
    """
    corpora = rag.list_corpora()
    return [
        {
            "corpus_name": corpus.name,
            "display_name": corpus.display_name,
            "create_time": corpus.create_time,
        }
        for corpus in corpora
    ]


def list_files_in_corpus(corpus_name: str) -> list[dict]:
    """Lists all files in a RagCorpus.

    Args:
        corpus_name: The name of the corpus to list files from. Make sure to use full name, not the display name.
    Returns: A list of dicts with file details.
    """
    files = rag.list_files(corpus_name)
    return [
        {
            "name": file.name,
            "display_name": file.display_name,
            "create_time": file.create_time,
        }
        for file in files
    ]


def rag_query(query: str, corpus_name: str) -> dict:
    """
    Query a Vertex AI RAG corpus with a user question and return relevant information.
    Args:
        corpus_name (str): The name of the corpus to query. Use full resource name from list_corpora results, not the display name.
        query (str): The text query to search for in the corpus
    Returns:
        dict: The query results and status
    """
    rag_retrieval_config = rag.RagRetrievalConfig(
        top_k=5,
        filter=rag.Filter(vector_distance_threshold=0.5),
    )

    response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=corpus_name,
            )
        ],
        text=query,
        rag_retrieval_config=rag_retrieval_config,
    )
    try:
        results = []
        if hasattr(response, "contexts") and response.contexts:
            for ctx_group in response.contexts.contexts:
                result = {
                    "source_uri": (
                        ctx_group.source_uri if hasattr(ctx_group, "source_uri") else ""
                    ),
                    "source_name": (
                        ctx_group.source_display_name
                        if hasattr(ctx_group, "source_display_name")
                        else ""
                    ),
                    "text": ctx_group.text if hasattr(ctx_group, "text") else "",
                    "score": ctx_group.score if hasattr(ctx_group, "score") else 0.0,
                }
                results.append(result)

        if not results:
            return {
                "status": "warning",
                "message": f"No results found in corpus '{corpus_name}' for query: '{query}'",
                "query": query,
                "corpus_name": corpus_name,
                "results": [],
                "results_count": 0,
            }

        return {
            "status": "success",
            "message": f"Successfully queried corpus '{corpus_name}'",
            "query": query,
            "corpus_name": corpus_name,
            "results": results,
            "results_count": len(results),
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Ran into an error while running a query: '{e}'",
        }


def create_rag_agent():
    rag_agent = Agent(
        name="rag_agent",
        model=config.RAG_AGENT_MODEL,
        description="A knowledge agent that uses a RAG corpus to store and retrieve information from documents.",
        instruction="""You are a knowledge agent that uses a RAG corpus to create/upload, store and retrieve information from documents in RAG store.
        If the user is asking you to upload documents to RAG storage - make sure to first list all avalable corpora and ask the user which corpus to save the document to.
        """,
        tools=[
            create_corpus,
            upload_files_to_corpus,
            delete_files_from_corpus,
            delete_corpus,
            list_corpora,
            list_files_in_corpus,
            rag_query,
        ],
        planner=config.RAG_AGENT_PLANNER,
        before_tool_callback=before_rag_edit_callback,
        output_key="rag_context"
    )
    return rag_agent
