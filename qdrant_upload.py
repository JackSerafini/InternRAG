import os
import re
import json
import pandas as pd
import torch

from haystack import Document
from haystack.document_stores.types import DuplicatePolicy

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

QDRANT_URL = "localhost:6333"
DINO_COLLECTION = "SEMImages_dino"
QWEN_COLLECTION = "SEMImages_qwen"
DINO_EMBEDDING_DIM = 768
QWEN_EMBEDDING_DIM = 4096

CROPS_FOLDER = "subset_test_1000/crops"
JSON_FOLDER = "subset_test_1000/json"
DINO_EMBEDDINGS_FOLDER = "subset_test_1000/embeddings"
QWEN_EMBEDDINGS_FOLDER = "subset_test_1000/embeddings_QWEN"

SETTINGS_KEYS = [
    "AP_WD",
    "AP_ALIAS_WD",
    "AP_FREE_WD",
    "AP_BEAM_TIME",
    "AP_STAGE_LOW_Z",
    "AP_STAGE_CENTRE_X",
    "AP_C3",
    "AP_EHT_CAL_30KV",
    "AP_EHT_CAL_10KV",
    "AP_EHT_CAL_100",
    "AP_EHT_CAL_24KV",
    "AP_MINMAG",
]

PAYLOAD_FIELDS_TO_INDEX = [
    {"field_name": key, "field_schema": "float"} for key in SETTINGS_KEYS
] + [
    {"field_name": "SEMImageID", "field_schema": "integer"},
]

# Matches: "<label> = <number> <unit>"  e.g. "WD = 3.198 mm"
_NUM_PATTERN = re.compile(r"=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([^\s=]*)\s*$")


def parse_value(raw_string):
    """
    Turn 'WD = 3.198 mm' into (3.198, 'mm').  
    Returns (None, None) if the string can't be parsed (e.g. field is None or empty in the source JSON).
    """
    if not raw_string:
        return None, None
    match = _NUM_PATTERN.search(raw_string)
    if not match:
        return None, None
    return float(match.group(1)), match.group(2)


def load_all_metadata(folder_path):
    """
    Take the JSON folder and parse each file to extract the ID and the `SETTINGS_KEY`.  
    Returns a Pandas dataframe where each row is a file and columns are its values.
    """
    all_rows = []

    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r") as f:
            data = json.load(f)

        row = {
            "SEMImageID": data["SEMImageID"],
            "ImageOriginalName": data["ImageOriginalName"],
            "ImageHashName": data["ImageHashName"],
            "ImageAVGHashName": data["ImageAVGHashName"],
        }

        for key in SETTINGS_KEYS:
            value, unit = parse_value(data.get(key))
            row[key] = value # numeric column, e.g. AP_WD = 3.198
            row[f"{key}_unit"] = unit # e.g. AP_WD_unit = "mm"

        all_rows.append(row)

    df = pd.DataFrame(all_rows)
    print(f"Loaded {len(df)} files.")
    return df


def load_embeddings(folder_path):
    """
    Take the embeddings (`.pt`) folder and load each file with `torch`.  
    Returns a dictionary of imageID: embedding.
    """
    embeddings = {}
    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith(".pt"):
            continue
        image_id = int(os.path.splitext(filename)[0])
        tensor = torch.load(os.path.join(folder_path, filename))
        embeddings[image_id] = tensor.flatten().tolist()
    return embeddings


def render_content(row):
    """
    Create content based on the metadata (from JSON).  
    Returns a string containing basic information about the image (not used during retrieval, only used by LLM to generate answer).
    """
    parts = [f"SEM image {row['SEMImageID']}."]
    if row["AP_WD"] is not None:
        parts.append(f"Working distance: {row['AP_WD']} {row['AP_WD_unit']}.")
    if row["AP_MINMAG"] is not None:
        parts.append(f"Minimum magnification: {row['AP_MINMAG']} {row['AP_MINMAG_unit']}.")
    if row["AP_C3"] is not None:
        parts.append(f"C3 lens current: {row['AP_C3']} {row['AP_C3_unit']}.")
    if row["AP_BEAM_TIME"] is not None:
        parts.append(f"Beam time: {row['AP_BEAM_TIME']} {row['AP_BEAM_TIME_unit']}.")
    return " ".join(parts)


def build_meta(row):
    """
    Build the metadata for filtering to append to the Document to upload to Qdrant.  
    Returns a dictionary of key: value.
    """
    meta = {
        "SEMImageID": int(row["SEMImageID"]),
        "ImageOriginalName": row["ImageOriginalName"],
        "ImageHashName": row["ImageHashName"],
    }
    for key in SETTINGS_KEYS:
        value = row[key]
        if value is not None:
            meta[key] = float(value)
    return meta


def build_documents(embeddings, json_folder):
    """
    Build the Haystack Document to upload to Qdrant.  
    Returns a list of Documents.
    """
    df = load_all_metadata(json_folder)
    documents = []
    skipped = []

    for _, row in df.iterrows():
        image_id = row["SEMImageID"]
        if image_id not in embeddings:
            skipped.append(image_id)
            continue

        documents.append(
            Document(
                id=str(image_id),
                content=render_content(row),
                embedding=embeddings[image_id],
                meta=build_meta(row),
            )
        )

    if skipped:
        print(f"Warning: {len(skipped)} image(s) had metadata but no embedding, skipped: {skipped[:10]}...")
    return documents


def build_collection(collection_name, embeddings_folder, embedding_dim, json_folder):
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
        url=QDRANT_URL,
    )

    embeddings = load_embeddings(embeddings_folder)
    documents = build_documents(embeddings, json_folder)
    document_store.write_documents(documents, policy=DuplicatePolicy.OVERWRITE)
    print(f"Wrote {len(documents)} documents to '{collection_name}' (dim={embedding_dim}), "
          f"indexed on {len(PAYLOAD_FIELDS_TO_INDEX)} payload fields.")
    return document_store


if __name__ == "__main__":
    print("--- Building DINO collection ---")
    build_collection(DINO_COLLECTION, DINO_EMBEDDINGS_FOLDER, DINO_EMBEDDING_DIM, JSON_FOLDER)
    # print("Skipped -- Already built.")

    print("\n--- Building QWEN collection ---")
    build_collection(QWEN_COLLECTION, QWEN_EMBEDDINGS_FOLDER, QWEN_EMBEDDING_DIM, JSON_FOLDER)
    # print("Skipped -- Already built.")