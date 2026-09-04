import json
import bm25s

from sem_rag.config.settings import SEMDataset, Evaluation


def main():
    with SEMDataset.DESCRIPTIONS.open("r", encoding="utf-8") as file:
        descriptions = json.load(file)

    corpus = [
        {
            "id": image_id,
            "text": description,
        } for image_id, description in descriptions.items()
    ]

    corpus_tokens = bm25s.tokenize([doc["text"] for doc in corpus])

    retriever = bm25s.BM25(corpus=corpus)
    retriever.index(corpus_tokens)

    Evaluation.BM25_DIR.mkdir(parents=True, exist_ok=True)

    retriever.save(str(Evaluation.BM25_DIR), corpus=corpus)
    print(f"BM25 index created successfully: {len(corpus):,} documents indexed → {Evaluation.BM25_DIR}")


if __name__ == "__main__":
    main()
