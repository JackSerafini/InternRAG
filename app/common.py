"""
Shared configuration and pipeline-building blocks used by both the
indexing service and the retrieval (chat) service.
"""
import os

from haystack.utils import Secret
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

VLLM_API_KEY = os.getenv("VLLM_API_KEY")
API_URL = os.getenv("VLLM_API_URL", "https://orfeo-llm.areasciencepark.it/vllm/v1")

EMBED_MODEL_ID = os.getenv("EMBED_MODEL_ID", "Qwen/Qwen3-Embedding-4B")
GENERATION_MODEL_ID = os.getenv("GENERATION_MODEL_ID", "Qwen/Qwen3.5-9B")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "2560")) # must match EMBED_MODEL_ID's output dim

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.orfeo-rag.svc.cluster.local:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "documents")

if not VLLM_API_KEY:
    raise RuntimeError("VLLM_API_KEY is not set.")

def get_document_store() -> QdrantDocumentStore:
    """
    Returns a QdrantDocumentStore pointing at the shared, persistent, in-cluster Qdrant instance.
    """
    return QdrantDocumentStore(
        url=QDRANT_URL,
        index=QDRANT_COLLECTION,
        embedding_dim=EMBEDDING_DIM,
    )

def get_vllm_secret() -> Secret:
    return Secret.from_token(VLLM_API_KEY)