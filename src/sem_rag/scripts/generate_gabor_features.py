from pathlib import Path

import numpy as np

from sem_rag.config.settings import SEMDataset, Evaluation
from sem_rag.retrieval.gabor import GaborDescriptor


def generate_features(crops_dir, output_path):
    crops_dir = Path(crops_dir)
    output_path = Path(output_path)

    descriptor = GaborDescriptor()

    crop_paths = sorted(crops_dir.glob("*.npy"))

    print(f"Found {len(crop_paths)} crops.")

    image_ids = []
    features = []

    for i, crop_path in enumerate(crop_paths, start=1):
        image_id = crop_path.name.split("_", 1)[0]

        image = np.load(crop_path)
        feature_vector = descriptor.extract(image)

        image_ids.append(image_id)
        features.append(feature_vector)

        if i % 100 == 0 or i == len(crop_paths):
            print(f"Processed {i}/{len(crop_paths)}")

    features = np.vstack(features)
    image_ids = np.asarray(image_ids)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output_path,
        image_ids=image_ids,
        features=features,
    )

    print()
    print(f"Saved: {output_path}")
    print(f"Image IDs: {image_ids.shape}")
    print(f"Features:  {features.shape}")


if __name__ == "__main__":
    generate_features(
        crops_dir=SEMDataset.CROPS,
        output_path=Evaluation.GABOR_FILE,
    )
