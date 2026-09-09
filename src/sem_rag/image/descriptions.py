import os
import json
import glob

from openai import OpenAI

from sem_rag.config.settings import VLLM, SEMDataset
from sem_rag.image.encoding import encode_image

client = OpenAI(base_url=VLLM.API_URL, api_key=VLLM.API_KEY)


def _generate_image_description(image_path: str) -> str:
    """
    Generate a scientific description of a SEM image using Gemma 4.

    The image is encoded as a base64 PNG data URL and sent to the
    configured Gemma model through the OpenAI-compatible vLLM API.

    Args:
        image_path: Path to the NumPy file containing the SEM image.

    Returns:
        A concise scientific description of the image, focusing on
        visible morphology, structure, particle shape, size, texture,
        and patterns.
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


def load_descriptions(descriptions_path: str) -> dict[str, str]:
    """
    Load cached image descriptions from a JSON file.

    If the file does not exist, an empty dictionary is returned.

    Args:
        descriptions_path: Path to the JSON file containing cached
            image descriptions.

    Returns:
        A dictionary mapping image IDs, stored as strings, to their
        corresponding descriptions.
    """
    if os.path.exists(descriptions_path):
        with open(descriptions_path, "r") as file:
            return json.load(file)
    return {}


def _save_descriptions(
        descriptions: dict[str, str],
        descriptions_path: str
) -> None:
    """
    Save cached image descriptions to a JSON file.

    Args:
        descriptions: Dictionary mapping image IDs to descriptions.
        descriptions_path: Path to the JSON file where the descriptions
            should be stored.
    """
    with open(descriptions_path, "w") as file:
        json.dump(
            descriptions,
            file,
            indent=2
        )


def get_crop_path(image_id: int) -> str:
    """
    Find the NumPy crop corresponding to a SEM image ID.

    The crop is expected to follow the naming convention
    `<image_id>_*.npy`.

    Args:
        image_id: SEM image identifier.

    Returns:
        The path to the unique crop associated with the image ID.
    """
    pattern = os.path.join(SEMDataset.CROPS, f"{image_id}_*.npy")

    matches = glob.glob(pattern)

    if not matches:
        raise FileNotFoundError(f"No crop found for image ID {image_id}")

    if len(matches) > 1:
        raise RuntimeError(f"Multiple crops found for image ID {image_id}: {matches}")

    return matches[0]


def get_description(
        image_id: int, 
        descriptions: dict[str, str]
) -> str:
    """
    Retrieve or generate the description for a SEM image.

    If a description already exists in the provided cache, it is returned
    without making a request to the VLM. Otherwise, the corresponding
    image crop is located, described using Gemma 4, added to the cache,
    and persisted to disk.

    The provided ``descriptions`` dictionary is modified in place when
    a new description is generated.

    Args:
        image_id: SEM image identifier.
        descriptions: In-memory cache mapping image IDs to descriptions.

    Returns:
        The cached or newly generated image description.
    """
    key = str(image_id)

    if key in descriptions:
        return descriptions[key]

    crop_path = get_crop_path(image_id)
    print(f"Generating description for image {image_id}")

    description = _generate_image_description(crop_path)
    
    descriptions[key] = description
    _save_descriptions(descriptions, SEMDataset.DESCRIPTIONS)

    return description
