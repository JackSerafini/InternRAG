# Evaluation

The evaluation lives in four notebooks under `notebooks/`. All of them use the reusable components in `src/sem_rag/retrieval/` (the same logic as the deployed wrappers) and need a valid vLLM token and access to the project Qdrant instance.

| Notebook | Dataset | What it measures |
| -------- | ------- | ---------------- |
| `EVAL_metadata_extraction.ipynb` | SEM schema | Accuracy of the `QueryMetadataExtractor` |
| `EVAL_text_retrieval.ipynb` | SEM | Text → image retrieval |
| `EVAL_image_retrieval.ipynb` | SEM | Image → image retrieval |
| `EVAL_end2end.ipynb` | LAME | Qualitative check of the full retrieval pipeline |

## Compared systems (retrieval notebooks)

* **BM25** over the generated image descriptions (`retrieval/bm25.py`, text queries only)
* **CLIP** (`SEM_clip`)
* **Gabor** texture features (`retrieval/gabor.py`, image queries only)
* **Qwen3-VL**: plain dense retrieval on `SEM_qwen`
* **InternRAG**: Qwen3-VL top 50 + MMR to 5, as in production (so only metrics at k ≤ 5)
* **Random** baseline

## Metadata extraction (`EVAL_metadata_extraction.ipynb`)

A hand-written test suite of queries with their expected Haystack filter, grouped into: numeric comparison / approx / between, categorical, dictionary (alias) terms for numeric and categorical fields, multiple constraints (numeric+numeric, categorical+categorical, mixed, three fields), and non-existing metadata (single and mixed with valid constraints). A case is correct if the produced filter equals the expected one (condition order ignored).

Results (identical across 5 runs; settings: JSON mode, temperature 0, thinking disabled):

| Model | Accuracy | Errors |
| ----- | -------- | ------ |
| `google/gemma-4-26B-A4B-it` | 100 % | – |
| `Qwen/Qwen3.6-35B-A3B-FP8` | 98.98 % | non-existing metadata, numeric aliases |
| `Qwen/Qwen3.8-27B-FP8` | 99.49 % | non-existing metadata |

Gemma was therefore kept as the extraction model.

## Text retrieval (`EVAL_text_retrieval.ipynb`)

1. **Category retrieval.** 5 queries per morphology category (50 in total, `named` and `descriptive` styles). An image is relevant if its human-assigned category matches. Metrics: P@5, P@10, nDCG@10, AP@50, overall, per category and per query style.
2. **Target retrieval** (known-item search). One generated query per sampled target image, stratified by visual isolation (mean cosine distance to the 5 nearest neighbours). Near-duplicates of the target are tracked. Metrics: Recall@1/5/10 and MRR. The generated queries are cached in `queries.json` so they can be reviewed by hand.

## Image retrieval (`EVAL_image_retrieval.ipynb`)

> [!NOTE]
> TODO

## End-to-end (`EVAL_end2end.ipynb`)

Rebuilds the `RAG-LAME` retrieval pipeline (embedder + metadata extractor + Qdrant top 50 + MMR top 5) on `LAME_qwen`. It runs four groups of queries (text, text + metadata, image, image + metadata) and plots the top-5 crops with their scores and metadata, so you can check by eye that the semantic match and the metadata filters behave as expected (e.g. "hexagonal spot pattern with magnification greater than 50kx", or "similar to this image, with E-T detector"). This evaluation is qualitative and the results from the researchers are expected soon.
