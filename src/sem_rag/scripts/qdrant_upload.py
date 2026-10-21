import argparse

import pandas as pd

from haystack import Document
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from sem_rag.config.settings import Qdrant, SEMDataset, LAMEDataset
from sem_rag.dataset import loader as sem_loader
from sem_rag.dataset import loader_lame as lame_loader
from sem_rag.image.descriptions import get_crop_path, load_descriptions, get_sem_description, get_lame_description
from sem_rag.image.encoding import encode_image


def render_content(
    row: pd.Series,
    image_id: int | str,
    numeric_fields: list[str],
    categorical_fields: list[str],
) -> str:
    """
    Build document text from an image identifier and its metadata.
    """
    parts = [f"SEM image {image_id}."]

    for field in numeric_fields:
        value = row.get(field)

        if pd.notna(value):
            unit = row.get(f"{field}_unit")
            if pd.notna(unit) and unit:
                parts.append(f"{field}: {value} {unit}.")
            else:
                parts.append(f"{field}: {value}.")

    for field in categorical_fields:
        value = row.get(field)

        if pd.notna(value):
            parts.append(f"{field}: {value}.")

    return " ".join(parts)


def build_meta(
    row: pd.Series,
    dataset_name: str,
    image_id: int | str,
    crop_path=None,
    include_thumbnail: bool = False,
) -> dict:
    """
    Build the Qdrant payload for filtering and displaying images.
    """
    if dataset_name == "sem":
        meta = {
            "SEMImageID": int(image_id),
            "ImageOriginalName": row["ImageOriginalName"],
            "ImageHashName": row["ImageHashName"],
        }
    else:
        meta = {"image_id": str(image_id)}

    numeric_fields = sem_loader.NUMERIC_FIELDS if dataset_name == "sem" else lame_loader.NUMERIC_FIELDS
    categorical_fields = sem_loader.CATEGORICAL_FIELDS if dataset_name == "sem" else lame_loader.CATEGORICAL_FIELDS

    for field in numeric_fields:
        value = row.get(field)
        if pd.notna(value):
            meta[field] = float(value)

    for field in categorical_fields:
        value = row.get(field)
        if pd.notna(value):
            meta[field] = str(value)

    if include_thumbnail:
        if dataset_name == "sem":
            crop_path = get_crop_path(int(image_id))

        dataset = SEMDataset if dataset_name == "sem" else LAMEDataset
        meta["thumb_b64"] = encode_image(crop_path, size=dataset.THUMBNAIL_SIZE)

    return meta


def build_documents(
    dataset_name: str,
    embeddings: dict,
    include_thumbnail: bool = False,
) -> list[Document]:
    """
    Build Haystack Documents from a dataset's metadata and embeddings.
    """
    if dataset_name == "sem":
        dataset = SEMDataset
        loader = sem_loader
        df = loader.load_all_metadata(dataset.JSON)
    else:
        dataset = LAMEDataset
        loader = lame_loader
        df = loader.load_all_metadata(dataset.META)

    descriptions = load_descriptions(dataset.DESCRIPTIONS)
    documents = []
    skipped = []

    for _, row in df.iterrows():
        image_id = int(row["SEMImageID"]) if dataset_name == "sem" else str(row["image_id"])

        if image_id not in embeddings:
            skipped.append(image_id)
            continue

        crop_path = None

        if dataset_name == "sem":
            description = get_sem_description(image_id, descriptions)
        else:
            crop_path = dataset.CROPS / f"{image_id}.npy"
            if not crop_path.exists():
                skipped.append(image_id)
                continue

            description = get_lame_description(crop_path, descriptions)

        content = render_content(row, image_id, loader.NUMERIC_FIELDS, loader.CATEGORICAL_FIELDS)
        content += "\n\nVisual description:\n" + description

        documents.append(
            Document(
                id=str(image_id),
                content=content,
                embedding=embeddings[image_id],
                meta=build_meta(
                    row,
                    dataset_name,
                    image_id,
                    crop_path=crop_path,
                    include_thumbnail=include_thumbnail,
                ),
            )
        )

    if skipped:
        print(f"Warning: {len(skipped)} image(s) skipped because their embedding or crop was missing: {skipped[:10]}")

    return documents


def build_collection(dataset_name: str):
    """
    Create a Qdrant collection and upload the selected dataset.
    """
    if dataset_name == "sem":
        dataset = SEMDataset
        loader = sem_loader
        collection_name = Qdrant.COLLECTION_QWEN
    else:
        dataset = LAMEDataset
        loader = lame_loader
        collection_name = Qdrant.COLLECTION_LAME

    embedding_dim = Qdrant.EMBEDDING_DIM_QWEN

    if embedding_dim is None:
        raise ValueError(f"embedding_dim not set for collection '{collection_name}'.")

    document_store = QdrantDocumentStore(
        url=Qdrant.URL,
        port=80,
        index=collection_name,
        embedding_dim=embedding_dim,
        recreate_index=True,
        payload_fields_to_index=loader.PAYLOAD_FIELDS_TO_INDEX,
        write_batch_size=20,
        timeout=60,
    )

    embeddings = loader.load_embeddings(dataset.EMBEDDINGS_QWEN)
    documents = build_documents(dataset_name, embeddings, include_thumbnail=True)

    document_store.write_documents(documents, policy=DuplicatePolicy.OVERWRITE)

    print(f"Wrote {len(documents)} documents to '{collection_name}' (dim={embedding_dim}), indexed on {len(loader.PAYLOAD_FIELDS_TO_INDEX)} payload fields.")

    return document_store


def main():
    """Upload the selected dataset to Qdrant."""
    parser = argparse.ArgumentParser(description="Upload SEM image embeddings and metadata to Qdrant.")
    parser.add_argument("--dataset", choices=["sem", "lame"], required=True, help="Dataset to upload.")
    args = parser.parse_args()

    print(f"\n--- Building {args.dataset.upper()} collection ---")
    build_collection(args.dataset)


if __name__ == "__main__":
    main()
