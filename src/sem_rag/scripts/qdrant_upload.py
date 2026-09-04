import pandas as pd

from haystack import Document
from haystack.document_stores.types import DuplicatePolicy

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from openai import OpenAI

# from sem_rag.config.settings import *
from sem_rag.config.settings import *
from sem_rag.utils.dataset import load_all_metadata, load_embeddings, NUMERIC_FIELDS, CATEGORICAL_FIELDS, PAYLOAD_FIELDS_TO_INDEX
from sem_rag.utils.image import encode_image
from sem_rag.utils.image_descriptions import get_crop_path, load_descriptions, get_description

client = OpenAI(base_url=VLLM.API_URL, api_key=VLLM.API_KEY)


def render_content(row):
    """
    Create textual content from canonical metadata.
    This content is provided to the LLM after retrieval.
    """
    parts = [f"SEM image {row['SEMImageID']}."]

    for field in NUMERIC_FIELDS:
        value = row.get(field)

        if pd.notna(value):
            unit = row.get(f"{field}_unit")

            if unit:
                parts.append(f"{field}: {value} {unit}.")
            else:
                parts.append(f"{field}: {value}.")

    for field in CATEGORICAL_FIELDS:
        value = row.get(field)

        if pd.notna(value):
            parts.append(f"{field}: {value}.")

    return " ".join(parts)


def build_meta(row, include_thumbnail=False):
    """
    Build the metadata for filtering to append to the Document to upload to Qdrant.  
    Returns a dictionary of key: value.
    """
    meta = {
        "SEMImageID": int(row["SEMImageID"]),
        "ImageOriginalName": row["ImageOriginalName"],
        "ImageHashName": row["ImageHashName"],
    }

    # Numeric metadata
    for field in NUMERIC_FIELDS:
        value = row.get(field)

        if pd.notna(value):
            meta[field] = float(value)

    # Categorical metadata
    for field in CATEGORICAL_FIELDS:
        value = row.get(field)

        if pd.notna(value):
            meta[field] = str(value)

    if include_thumbnail:
        crop_path = get_crop_path(int(row["SEMImageID"]))
        meta["thumb_b64"] = encode_image(crop_path, size=SEMDataset.THUMBNAIL_SIZE)
    
    return meta


def build_documents(embeddings, json_folder, descriptions_path, include_thumbnail=False):
    """
    Build the Haystack Document to upload to Qdrant.  
    Returns a list of Documents.
    """
    df = load_all_metadata(json_folder)
    descriptions = load_descriptions(descriptions_path)
    documents = []
    skipped = []

    for _, row in df.iterrows():
        image_id = row["SEMImageID"]
        if image_id not in embeddings:
            skipped.append(image_id)
            continue

        description = get_description(image_id, descriptions)
        content = render_content(row)

        content += (
            "\n\nVisual description:\n"
            + description
        )

        documents.append(
            Document(
                id=str(image_id),
                content=content,
                embedding=embeddings[image_id],
                meta=build_meta(row, include_thumbnail=include_thumbnail),
            )
        )

    if skipped:
        print(f"Warning: {len(skipped)} image(s) had metadata but no embedding, skipped: {skipped[:10]}...")
    return documents


def build_collection(collection_name, embeddings_folder, embedding_dim, json_folder, descriptions_path, include_thumbnail=False):
    if embedding_dim is None:
        raise ValueError(
            f"embedding_dim not set for collection '{collection_name}' -- "
            f"fill in the actual output dimension before running."
        )

    document_store = QdrantDocumentStore(
        index=collection_name,
        embedding_dim=embedding_dim,
        recreate_index=True,
        payload_fields_to_index=PAYLOAD_FIELDS_TO_INDEX,
        write_batch_size=20,
        timeout=60,
        url=Qdrant.URL,
    )

    embeddings = load_embeddings(embeddings_folder)
    documents = build_documents(embeddings, json_folder, descriptions_path, include_thumbnail=include_thumbnail)
    document_store.write_documents(documents, policy=DuplicatePolicy.OVERWRITE)
    print(f"Wrote {len(documents)} documents to '{collection_name}' (dim={embedding_dim}), "
          f"indexed on {len(PAYLOAD_FIELDS_TO_INDEX)} payload fields.")
    return document_store


if __name__ == "__main__":
    print("\n--- Building SEM collection ---")
    build_collection(Qdrant.COLLECTION_QWEN, SEMDataset.EMBEDDINGS_QWEN, Qdrant.EMBEDDING_DIM_QWEN, SEMDataset.JSON, SEMDataset.DESCRIPTIONS, include_thumbnail=True)
    # print("Skipped -- Already built.")
