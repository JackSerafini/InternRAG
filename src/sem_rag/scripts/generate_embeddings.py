import argparse

import torch
from tqdm import tqdm

from sem_rag.config.settings import SEMDataset, LAMEDataset
from sem_rag.embedding.embedder import QwenEmbedder


def generate_embeddings(dataset):
    """
    Generate and save Qwen image embeddings for a dataset.
    """
    dataset.EMBEDDINGS_QWEN.mkdir(parents=True, exist_ok=True)

    crop_paths = sorted(dataset.CROPS.glob("*.npy"))
    embedder = QwenEmbedder()

    for crop_path in tqdm(crop_paths, desc="Generating Qwen embeddings"):
        if dataset is SEMDataset:
            image_id = crop_path.stem.split("_")[0]
        else:
            image_id = crop_path.stem
        out_path = dataset.EMBEDDINGS_QWEN / f"{image_id}.pt"

        if out_path.exists():
            continue

        embedding = embedder.embed_image(crop_path)
        torch.save(torch.tensor(embedding), out_path)

    print(f"Qwen embedding generation complete: {len(crop_paths):,} crops processed → {dataset.EMBEDDINGS_QWEN}")


def main():
    parser = argparse.ArgumentParser(description="Generate Qwen embeddings for a dataset.")
    parser.add_argument("--dataset", choices=["sem", "lame"], required=True, help="Dataset to process.")
    args = parser.parse_args()

    dataset = SEMDataset if args.dataset == "sem" else LAMEDataset
    generate_embeddings(dataset)


if __name__ == "__main__":
    main()
