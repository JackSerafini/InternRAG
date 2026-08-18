import os
import json

import pandas as pd
import torch

from config.settings import SEMDataset
from utils.metadata import parse_category, parse_value_with_unit, parse_pixel_size, parse_magnification


def load_field_dictionaries() -> tuple[
    pd.DataFrame, 
    pd.DataFrame, 
    dict[str, list[str]], 
    dict[str, list[str]]
]:
    """
    Load and build mappings between canonical metadata fields and JSON fields.

    The numerical and categorical field definitions are read from the
    corresponding CSV configuration files. Multiple JSON fields can map to
    the same canonical field; they are stored in priority order as defined
    by the CSV files.

    Returns:
        A tuple containing:
            - DataFrame containing numerical field definitions.
            - DataFrame containing categorical field definitions.
            - Mapping from canonical numerical fields to JSON field names.
            - Mapping from canonical categorical fields to JSON field names.
    """
    numeric_df = pd.read_csv(SEMDataset.NUMERICAL_SETTINGS, sep=";")
    categorical_df = pd.read_csv(SEMDataset.CATEGORICAL_SETTINGS, sep=";")

    numeric_map = {
        row["canonical_field"]: [
            field.strip()
            for field in row["json_fields"].split(",")
        ] for _, row in numeric_df.iterrows()
    }

    categorical_map = {
        row["canonical_field"]: [
            field.strip()
            for field in row["json_fields"].split(",")
        ] for _, row in categorical_df[categorical_df["canonical_field"] != "category"].drop_duplicates(subset=["canonical_field"]).iterrows()
    }

    return numeric_df, categorical_df, numeric_map, categorical_map


NUMERIC_FIELDS_DF, CATEGORICAL_FIELDS_DF, NUMERIC_MAP, CATEGORICAL_MAP = load_field_dictionaries()

NUMERIC_FIELDS: list[str] = NUMERIC_FIELDS_DF["canonical_field"].unique().tolist()

CATEGORICAL_FIELDS: list[str] = CATEGORICAL_FIELDS_DF["canonical_field"].unique().tolist()

categories_df = pd.read_csv(SEMDataset.CATEGORIES)
CATEGORY_MAP: dict[int, str] = dict(zip(categories_df["TIF_SEMImageID"], categories_df["mapped_category"]))


PAYLOAD_FIELDS_TO_INDEX: list[dict[str, str]] = [
    {"field_name": field, "field_schema": "float"}
    for field in NUMERIC_FIELDS
] + [
    {"field_name": field, "field_schema": "keyword"}
    for field in CATEGORICAL_FIELDS
] + [
    {"field_name": "SEMImageID", "field_schema": "integer"},
]


def load_all_metadata(folder_path: str) -> pd.DataFrame:
    """
    Load and parse SEM metadata from a folder of JSON files.

    Each JSON file is expected to contain a ``SEMImageID`` together with
    the metadata fields defined by the numerical and categorical field
    configuration. JSON field names are mapped to canonical field names
    and their values are parsed and normalized where necessary.

    Args:
        folder_path: Path to the folder containing the SEM metadata JSON
            files.

    Returns:
        A DataFrame where each row represents one SEM image and each
        column contains a canonical metadata field.

    Notes:
        Numerical values are parsed together with their units. Pixel sizes
        are normalized to nanometers per pixel, while magnification values
        are normalized to a numeric value with unit ``X``.
    """
    all_rows = []

    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r") as file:
            data = json.load(file)

        image_id = int(data["SEMImageID"])

        row = {
            "SEMImageID": image_id,
            "ImageOriginalName": data["ImageOriginalName"],
            "ImageHashName": data["ImageHashName"],
            "ImageAVGHashName": data["ImageAVGHashName"],
        }

        # Numeric fields
        for canonical_field, json_fields in NUMERIC_MAP.items():
            value = None
            unit = None

            for json_field in json_fields:
                raw_value = data.get(json_field)

                if canonical_field == "pixel_size_nm":
                    parsed_value, parsed_unit = parse_pixel_size(raw_value, json_field)
                elif canonical_field == "magnification_x":
                    parsed_value, parsed_unit = parse_magnification(raw_value)
                else:
                    parsed_value, parsed_unit = parse_value_with_unit(raw_value)

                if parsed_value is not None:
                    value = parsed_value
                    unit = parsed_unit
                    break

            row[canonical_field] = value
            if unit:
                row[f"{canonical_field}_unit"] = unit

        # External category annotation
        row["category"] = CATEGORY_MAP.get(image_id)

        # Categorical field ("detector")
        for canonical_field, json_fields in CATEGORICAL_MAP.items():
            value = None

            for json_field in json_fields:
                raw_value = data.get(json_field)
                parsed_value = parse_category(raw_value)

                if parsed_value is not None:
                    value = parsed_value
                    break

            row[canonical_field] = value

        all_rows.append(row)

    df = pd.DataFrame(all_rows)
    print(f"Loaded {len(df)} files.")

    return df


def load_embeddings(folder_path: str) -> dict[int, list[float]]:
    """
    Load precomputed image embeddings from a folder of PyTorch files.

    Each ``.pt`` file is expected to be named using its corresponding
    SEM image ID, for example ``12345.pt``. Loaded tensors are flattened
    and converted to Python lists.

    Args:
        folder_path: Path to the folder containing the embedding files.

    Returns:
        A dictionary mapping each SEM image ID to its embedding vector.
    """
    embeddings: dict[int, list[float]] = {}

    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith(".pt"):
            continue

        image_id = int(os.path.splitext(filename)[0])

        tensor = torch.load(os.path.join(folder_path, filename))

        embeddings[image_id] = tensor.flatten().tolist()
    
    return embeddings
