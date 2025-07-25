import os
from pinecone import Pinecone, ServerlessSpec, QueryResponse, NotFoundException
from dotenv import load_dotenv
from vertexai.language_models import TextEmbeddingModel

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Load environment variables
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', "")
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', "")

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
            metric='cosine',
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
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

def query_vectors(vector: list[float], top_k: int = 5, namespace: str | None = None, include_metadata: bool = True, filters: dict | None = None) -> list[dict]:
    """Queries the Pinecone index and returns results with metadata."""
    index = get_pinecone_index()
    query_results = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=include_metadata,
        namespace=namespace,
        filter=filters
    )
    results = []
    if not isinstance(query_results, QueryResponse):
        raise ValueError("Query response is not of type QueryResponse")
    for match in query_results.matches:
        results.append({
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata
        })
    return results

def delete_vectors(ids: list[str], namespace: str | None = None):
    """Deletes vectors from the Pinecone index by ID."""
    index = get_pinecone_index()
    index.delete(ids=ids, namespace=namespace)
