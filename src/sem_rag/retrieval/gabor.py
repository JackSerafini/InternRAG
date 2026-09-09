from pathlib import Path

import numpy as np
from skimage.filters import gabor
from skimage.transform import resize


class GaborDescriptor:
    """Extract Gabor texture features from an image."""

    ORIENTATIONS = [
        0,
        np.pi / 4,
        np.pi / 2,
        3 * np.pi / 4,
    ]

    FREQUENCIES = [
        0.1,
        0.2,
        0.4,
    ]

    IMAGE_SIZE = (128, 128)

    def extract(self, image: np.ndarray) -> np.ndarray:
        """
        Extract a Gabor feature vector from an image.

        The image is first normalized and resized. A Gabor filter is then
        applied for each combination of orientation and frequency. The
        magnitude of each filter response is summarized using its mean and
        standard deviation.

        Args:
            image: Input grayscale image as a NumPy array.

        Returns:
            A one-dimensional NumPy array containing the extracted Gabor
            features.
        """
        image = self._preprocess(image)

        features = []

        for theta in self.ORIENTATIONS:
            for frequency in self.FREQUENCIES:
                real, imag = gabor(
                    image,
                    frequency=frequency,
                    theta=theta,
                )

                magnitude = np.sqrt(real**2 + imag**2)

                features.append(magnitude.mean())
                features.append(magnitude.std())

        return np.asarray(features, dtype=np.float32)

    @classmethod
    def _preprocess(cls, image: np.ndarray) -> np.ndarray:
        """
        Normalize and resize an input image before feature extraction.

        Pixel intensities are normalized to the [0, 1] range and the image
        is resized to the configured resolution.

        Args:
            image: Input grayscale image as a NumPy array.

        Returns:
            A float32 image normalized to [0, 1] and resized to IMAGE_SIZE.
        """
        image = image.astype(np.float32)

        image_min = image.min()
        image_max = image.max()

        if image_max > image_min:
            image = (image - image_min) / (image_max - image_min)
        else:
            image = np.zeros_like(image)

        image = resize(
            image,
            cls.IMAGE_SIZE,
            anti_aliasing=True,
        )

        return image.astype(np.float32)


class GaborRetriever:
    """Retrieve images using Gabor feature similarity."""

    def __init__(self, features_path: str | Path):
        """
        Initialize the retriever from precomputed Gabor features.

        Args:
            features_path: Path to the NPZ file containing the image IDs
                and their corresponding Gabor feature vectors.
        """
        data = np.load(features_path)

        self.image_ids = data["image_ids"]
        self.features = data["features"]

        self.descriptor = GaborDescriptor()

    def retrieve(
        self,
        image: np.ndarray,
        top_k: int = 5,
    ) -> list[str]:
        """
        Retrieve the most similar images for a query image.

        The query image is converted into a Gabor feature vector and its
        Euclidean distance to every precomputed feature vector is calculated.
        Images with the smallest distances are returned.

        Args:
            image: Query grayscale image as a NumPy array.
            top_k: Number of most similar images to return.

        Returns:
            A list containing the IDs of the top-k most similar images.
        """
        query_features = self.descriptor.extract(image)

        distances = np.linalg.norm(
            self.features - query_features,
            axis=1,
        )

        indices = np.argsort(distances)[:top_k]

        return self.image_ids[indices].tolist()
