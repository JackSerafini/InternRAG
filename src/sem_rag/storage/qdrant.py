from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from sem_rag.config.settings import Qdrant

def get_document_store(
        collection_name: str,
        embedding_dim: int,
        recreate_index: bool = False,
        payload_fields_to_index: list[dict] | None = None
) -> QdrantDocumentStore:
    """
    Returns a QdrantDocumentStore pointing at the shared, persistent, in-cluster Qdrant instance.
    """
    return QdrantDocumentStore(
        url=Qdrant.URL,
        port=80,
        index=collection_name,
        embedding_dim=embedding_dim,
        recreate_index=recreate_index,
        payload_fields_to_index=payload_fields_to_index,
        write_batch_size=20,
        timeout=60,
    )
