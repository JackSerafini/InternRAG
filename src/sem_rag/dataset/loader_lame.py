from pathlib import Path

import pandas as pd
import torch

from sem_rag.dataset.metadata_lame import CATEGORICAL_FIELDS, NUMERIC_FIELDS, load_hdr_metadata


PAYLOAD_FIELDS_TO_INDEX: list[dict[str, str]] = [
    {"field_name": field, "field_schema": "float"} for field in NUMERIC_FIELDS
] + [
    {"field_name": field, "field_schema": "keyword"} for field in CATEGORICAL_FIELDS
] + [
    {"field_name": "image_id", "field_schema": "keyword"},
]


def load_all_metadata(folder_path: str | Path) -> pd.DataFrame:
    """
    Load SEM acquisition metadata from a folder of .hdr files.

    Each row represents one image. The image_id is derived from the
    header filename stem and is used to associate metadata with the
    corresponding crop and embedding.

    Args:
        folder_path: Folder containing .hdr files.

    Returns:
        A DataFrame with one row per header and canonical metadata fields.
    """
    folder_path = Path(folder_path)
    all_rows = []

    for hdr_path in sorted(folder_path.glob("*.hdr")):
        metadata = load_hdr_metadata(hdr_path)

        all_rows.append({
            "image_id": hdr_path.stem,
            **metadata,
        })

    df = pd.DataFrame(all_rows)

    multi = df["detector"].str.contains(",", na=False)
    df = df[~multi].reset_index(drop=True)
    
    print(f"Loaded metadata for {len(df)} images.")

    return df


def load_embeddings(folder_path: str | Path) -> dict[str, list[float]]:
    """
    Load precomputed image embeddings from PyTorch files.

    Each .pt file is expected to be named after its corresponding
    crop, for example ``sample--image.pt``.

    Args:
        folder_path: Folder containing the embedding files.

    Returns:
        A dictionary mapping image filename stems to embedding vectors.
    """
    folder_path = Path(folder_path)
    embeddings: dict[str, list[float]] = {}

    for embedding_path in sorted(folder_path.glob("*.pt")):
        tensor = torch.load(embedding_path)

        embeddings[embedding_path.stem] = tensor.flatten().tolist()

    return embeddings
