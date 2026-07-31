import os
import glob
import re
import io
import json
import base64
from PIL import Image
import numpy as np
import pandas as pd
import torch

from haystack import Document
from haystack.document_stores.types import DuplicatePolicy

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from openai import OpenAI

from sem_rag.config.settings import *

client = OpenAI(base_url=VLLM.API_URL, api_key=VLLM.API_KEY)

PAYLOAD_FIELDS_TO_INDEX = [
    {"field_name": key, "field_schema": "float"} for key in TestSem.SETTINGS_KEYS
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

        for key in TestSem.SETTINGS_KEYS:
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


def encode_image(path, size=None):
    arr = np.load(path)
    image = Image.fromarray(arr, mode="L")
    if size is not None:
        image = image.resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def generate_image_description(image_path):
    """
    Ask Gemma 4 to describe a SEM image.
    """
    image_url = encode_image(image_path)

    response = client.chat.completions.create(
        model=VLLM.GEMMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert in scanning electron microscopy. "
                    "Describe the image focusing on morphology, structure, "
                    "particle shape, size, texture, and visible patterns. "
                    "Do not invent information that is not visible."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this SEM image. "
                            "Provide a concise scientific description."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def load_descriptions():
    if os.path.exists(TestSem.DESCRIPTIONS):
        with open(TestSem.DESCRIPTIONS, "r") as f:
            return json.load(f)
    return {}

def save_descriptions(descriptions):
    with open(TestSem.DESCRIPTIONS, "w") as f:
        json.dump(
            descriptions,
            f,
            indent=2
        )


def get_crop_path(image_id):
    pattern = os.path.join(
        TestSem.CROPS,
        f"{image_id}_*.npy"
    )

    matches = glob.glob(pattern)

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No crop found for image ID {image_id}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple crops found for image ID {image_id}: {matches}"
        )

    return matches[0]


def get_description(image_id):
    descriptions = load_descriptions()

    key = str(image_id)
    if key in descriptions:
        return descriptions[key]

    crop_path = get_crop_path(image_id)
    print(f"Generating description for image {image_id}")

    description = generate_image_description(crop_path)
    descriptions[key] = description
    save_descriptions(descriptions)

    return description


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
    for key in TestSem.SETTINGS_KEYS:
        value = row[key]
        if value is not None:
            meta[key] = float(value)

    if include_thumbnail:
        crop_path = get_crop_path(int(row["SEMImageID"]))
        meta["thumb_b64"] = encode_image(crop_path, size=TestSem.THUMBNAIL_SIZE)
    
    return meta


def build_documents(embeddings, json_folder, include_thumbnail=False):
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

        description = get_description(image_id)
        content = render_content(row)
        content += "\n\nVisual description:\n" + description

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


def build_collection(collection_name, embeddings_folder, embedding_dim, json_folder, include_thumbnail=False):
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
    documents = build_documents(embeddings, json_folder, include_thumbnail=include_thumbnail)
    document_store.write_documents(documents, policy=DuplicatePolicy.OVERWRITE)
    print(f"Wrote {len(documents)} documents to '{collection_name}' (dim={embedding_dim}), "
          f"indexed on {len(PAYLOAD_FIELDS_TO_INDEX)} payload fields.")
    return document_store


if __name__ == "__main__":
    print("--- Building DINO collection ---")
    build_collection(Qdrant.COLLECTION_DINO, TestSem.EMBEDDINGS_DINO, Qdrant.EMBEDDING_DIM_DINO, TestSem.JSON, include_thumbnail=False)
    # print("Skipped -- Already built.")

    print("\n--- Building QWEN collection ---")
    build_collection(Qdrant.COLLECTION_QWEN, TestSem.EMBEDDINGS_QWEN, Qdrant.EMBEDDING_DIM_QWEN, TestSem.JSON, include_thumbnail=True)
    # print("Skipped -- Already built.")