import torch
from tqdm import tqdm

from sem_rag.config.settings import SEMDataset
from sem_rag.embedding.embedder import QwenEmbedder


def main():
    SEMDataset.EMBEDDINGS_QWEN.mkdir(parents=True, exist_ok=True)

    crop_paths = sorted(SEMDataset.CROPS.glob("*.npy"))

    embedder = QwenEmbedder()

    for crop_path in tqdm(crop_paths, desc="Generating Qwen embeddings"):
        image_id = crop_path.stem.split("_")[0]
        out_path = SEMDataset.EMBEDDINGS_QWEN / f"{image_id}.pt"

        if out_path.exists():
            continue

        embedding = embedder.embed_image(crop_path)

        torch.save(torch.tensor(embedding), out_path)

    print(f"Qwen embedding generation complete: {len(crop_paths):,} crops processed → {SEMDataset.EMBEDDINGS_QWEN}")


if __name__ == "__main__":
    main()
