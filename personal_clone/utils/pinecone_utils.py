import os
import streamlit as st
from pinecone import Pinecone, ServerlessSpec, QueryResponse, NotFoundException
from dotenv import load_dotenv
from vertexai.language_models import TextEmbeddingModel
import json
import tempfile

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# Load environment variables
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", st.secrets["PINECONE_API_KEY"])
PINECONE_INDEX_NAME = os.environ.get(
    "PINECONE_INDEX_NAME", st.secrets["PINECONE_INDEX_NAME"]
)

# Handle Google Cloud service account credentials for Vertex AI
if "gcp_service_account" in st.secrets:
    gcp_service_account_info = st.secrets["gcp_service_account"]
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".json"
    ) as temp_key_file:
        json.dump(dict(gcp_service_account_info), temp_key_file)
        temp_key_file_path = temp_key_file.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_file_path

# Initialize clients
pc = Pinecone(api_key=PINECONE_API_KEY)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")


def get_pinecone_index():
    """Ensures the Pinecone index exists and returns it."""
    try:
        pc.describe_index(PINECONE_INDEX_NAME)
    except NotFoundException:
        print(f"Pinecone index '{PINECONE_INDEX_NAME}' not found, creating it...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=768,  # Dimension for text-embedding-004
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"Pinecone index '{PINECONE_INDEX_NAME}' created successfully.")
    return pc.Index(PINECONE_INDEX_NAME)


def generate_embedding(text: str) -> list[float]:
    """Generates an embedding for the given text using Google's model."""
    embeddings = embedding_model.get_embeddings([text])
    return embeddings[0].values


def upsert_vectors(vectors: list[tuple], namespace: str | None = None):
    """Upserts vectors to the Pinecone index."""
    index = get_pinecone_index()
    index.upsert(vectors=vectors, namespace=namespace)


def query_vectors(
    vector: list[float],
    top_k: int = 5,
    namespace: str | None = None,
    include_metadata: bool = True,
    filters: dict | None = None,
) -> list[dict]:
    """Queries the Pinecone index and returns results with metadata."""
    index = get_pinecone_index()
    query_results = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=include_metadata,
        namespace=namespace,
        filter=filters,
    )
    results = []
    if not isinstance(query_results, QueryResponse):
        raise ValueError("Query response is not of type QueryResponse")
    for match in query_results.matches:
        results.append(
            {"id": match.id, "score": match.score, "metadata": match.metadata}
        )
    return results


def delete_vectors(ids: list[str], namespace: str | None = None):
    """Deletes vectors from the Pinecone index by ID."""
    index = get_pinecone_index()
    index.delete(ids=ids, namespace=namespace)
