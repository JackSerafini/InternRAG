from haystack import Document
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from sem_rag.config.settings import *
from sem_rag.dataset.loader import load_embeddings


def build_collection(collection_name, embeddings_folder, embedding_dim):
    if embedding_dim is None:
        raise ValueError(f"embedding_dim not set for collection '{collection_name}' -- fill in the actual output dimension before running.")

    document_store = QdrantDocumentStore(
        url=Qdrant.URL,
        port=80,
        index=collection_name,
        embedding_dim=embedding_dim,
        recreate_index=True,
        write_batch_size=20,
        timeout=60,
    )

    embeddings = load_embeddings(embeddings_folder)

    documents = [
        Document(
            id=str(image_id),
            embedding=embedding,
        ) for image_id, embedding in embeddings.items()
    ]

    document_store.write_documents(documents, policy=DuplicatePolicy.OVERWRITE)

    print(f"Wrote {len(documents)} documents to '{collection_name}' (dim={embedding_dim}).")

    return document_store


if __name__ == "__main__":
    print("\n--- Building CLIP collection ---")

    build_collection(
        Qdrant.COLLECTION_CLIP,
        SEMDataset.EMBEDDINGS_CLIP,
        Qdrant.EMBEDDING_DIM_CLIP,
    )
