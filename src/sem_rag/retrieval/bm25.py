from pathlib import Path

import bm25s


class BM25Retriever:
    """Retrieve image descriptions using a pre-built BM25 index."""

    def __init__(self, index_dir: str | Path):
        """Load a BM25 index from the specified directory.

        Args:
            index_dir: Directory containing the persisted BM25 index.
        """
        index_dir = Path(index_dir)
        if not index_dir.is_dir():
            raise FileNotFoundError(f"BM25 index directory not found at {index_dir}. Run the BM25 indexing script first.")
        
        self.retriever = bm25s.BM25.load(str(index_dir), load_corpus=True)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Retrieve the most relevant image descriptions for a query.

        Args:
            query: Text query used to search the BM25 index.
            top_k: Maximum number of results to return.

        Returns:
            A list of dictionaries containing the image ID, description,
            and BM25 relevance score for each retrieved result.
        """
        query_tokens = bm25s.tokenize(query)

        results, scores = self.retriever.retrieve(query_tokens, k=top_k)

        return [
            {
                "image_id": result["id"],
                "description": result["text"],
                "score": float(score),
            } for result, score in zip(results[0], scores[0])
        ]
