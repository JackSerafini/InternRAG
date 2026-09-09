import io
import base64
from pathlib import Path

import numpy as np
from PIL import Image


def encode_image(
        path: Path, 
        size: tuple[int, int] | None = None
) -> str:
    """
    Encode a NumPy image stored in a `.npy` file as a base64 PNG data URL.

    The NumPy array is interpreted as a grayscale image and converted to
    a PNG image in memory. The resulting PNG is base64-encoded and returned
    as a data URL suitable for use in APIs that accept image URLs.

    Args:
        path: Path to the `.npy` file containing the image array.
        size: Optional target size as `(width, height)`. If provided, the
            image is resized using Lanczos resampling before encoding.

    Returns:
        A base64-encoded PNG data URL in the form
        `data:image/png;base64,<encoded_image>`
    """
    array = np.load(path)
    image = Image.fromarray(array, mode="L")

    if size is not None:
        image = image.resize(size, Image.Resampling.LANCZOS)
    
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{encoded_image}"


def load_image_CLIP(path: Path) -> Image.Image:
    """
    Load a NumPy image and convert it to an RGB PIL image.

    Args:
        path: Path to the `.npy` file containing the image array.

    Returns:
        The image as an RGB PIL image.
    """
    array = np.load(path)
    image = Image.fromarray(array, mode="L").convert("RGB")

    return image
