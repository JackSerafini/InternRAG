# Configuration

InternRAG keeps project-wide configuration in:

```text
src/sem_rag/config/settings.py
```

The configuration is organized into several sections:
* Project paths and directories
* External services and models
* Dataset-specific paths
* SEM metadata fields
* Qdrant configuration

Environment-specific secrets, such as API keys, are loaded from environment variables rather than being stored directly in the source code.

## Environment Variables

InternRAG uses `python-dotenv` to load environment variables from a `.env` file.  
The following variables are currently used:

| Variable       | Used by | Description |
| -------------- | ------- | ----------- |
| `HF_TOKEN`     | `settings.HF_TOKEN` | Hugging Face token (model downloads, e.g. CLIP) |
| `VLLM_API_KEY` | `settings.VLLM.API_KEY`, all wrappers | Bearer token sent to the vLLM gateway (see *vLLM authentication* below) |
| `VLLM_API_URL` | `settings.VLLM.API_URL`, all wrappers | Base URL of the OpenAI-compatible vLLM API. Default: `https://orfeo-llm.areasciencepark.it/vllm/v1` |
| `QDRANT_URL`   | pipeline wrappers, `render/app.py` (in-cluster only) | Qdrant URL inside the cluster. Default: `http://qdrant.orfeo-rag.svc.cluster.local:6333` |
| `THUMBNAIL_BASE_URL` | pipeline wrappers | Public base URL of the thumbnail endpoint. Default: `https://llm-rag.dev.rd.areasciencepark.it/rag-images` |

Local `.env` example:
```text
HF_TOKEN=<your Hugging Face token>
VLLM_API_KEY=<token, see below>
```

## vLLM authentication

The vLLM gateway does not accept a static API key. It expects a JWT issued  with the `request_token.bash` script. It must be **sourced**, not executed, so that it can export `$JWT` into the current shell:

```bash
source request_token.bash
echo $JWT
```

Then you can copy and paste the content inside your `.env` file.

# Project Paths

The project root is determined automatically from the location of `settings.py`.  
The following directories are currently defined:

| Setting        | Description                                           |
| -------------- | ----------------------------------------------------- |
| `PROJECT_ROOT` | Root directory of the repository                      |
| `DATA_DIR`     | Root directory containing datasets and generated data |
| `NOTEBOOK_DIR` | Directory containing development notebooks            |

The paths are constructed using `pathlib.Path`, making them independent of the operating system's path separator.  
The expected structure is:
```text
project/
├── data/
├── notebooks/
└── src/
    └── sem_rag/
        └── config/
            └── settings.py
```

# vLLM

The `VLLM` configuration class contains settings related to the models served through the vLLM API:

| Setting           | Value                          | Description                                |
| ----------------- | ------------------------------ | ------------------------------------------ |
| `API_KEY`         | `VLLM_API_KEY`                 | Bearer token for the vLLM gateway          |
| `API_URL`         | `VLLM_API_URL` / default       | Base URL of the vLLM OpenAI-compatible API |
| `GEMMA_MODEL`     | `google/gemma-4-26B-A4B-it`    | Generation and metadata-extraction model   |
| `QWEN36_MODEL`    | `Qwen/Qwen3.6-35B-A3B-FP8`     | Alternative extractor (metadata-extraction evaluation) |
| `QWEN38_MODEL`    | `Qwen/Qwen3.8-27B-FP8`         | Alternative extractor (metadata-extraction evaluation) |
| `EMBEDDING_MODEL` | `Qwen/Qwen3-VL-Embedding-8B`   | Multimodal embedding model                 |

The pipeline wrappers do **not** read `settings.py`; they hard-code their own model IDs and collection names at the top of each `pipeline_wrapper.py`.

# Datasets

## SEM dataset (`SEMDataset`)

Located under `data/SEM/` (≈14k images, annotated with 10 morphology categories by Aversa et al.).

| Setting                | Path | Description |
| ---------------------- | ---- | ----------- |
| `CROPS`                | `crops/` | Image crops as `.npy`, named `<SEMImageID>_*.npy` |
| `JSON`                 | `json/` | Per-image metadata JSON |
| `EMBEDDINGS_QWEN`      | `embeddings_QWEN/` | Qwen3-VL embeddings (`<SEMImageID>.pt`) |
| `EMBEDDINGS_CLIP`      | `embeddings_CLIP/` | CLIP embeddings (baseline) |
| `EMBEDDINGS_DINO`      | `embeddings_DINOv3/` | DINOv3 embeddings (experiments) |
| `NUMERICAL_SETTINGS`   | `SEM_RAG_numeric_fields_dictionary.csv` | Canonical numeric field → JSON keys (in priority order) |
| `CATEGORICAL_SETTINGS` | `SEM_RAG_categorical_fields_dictionary.csv` | Canonical categorical field → JSON keys |
| `CATEGORIES`           | `filtered_categories.csv` | `SEMImageID` → human-assigned category |
| `DESCRIPTIONS`         | `image_descriptions.json` | Generated visual descriptions |

Canonical fields stored in Qdrant: `pixel_size_nm`, `magnification_x`, `accelerating_voltage_kv`, `working_distance_mm`, `brightness_percent`, `contrast_percent`, `scan_speed_setting`, `frame_average_count`, `line_average_count` (numeric), `category`, `detector` (categorical).

## LAME dataset (`LAMEDataset`)

The raw images are in `data/LAME/` (`SOURCE_DIR`). `notebooks/lame_images.ipynb` keeps only the images that have an `.hdr` metadata file and are larger than 512×512. It crops them, converts them to grayscale and writes them to `data/LAME_filtered/` (`LAME_DIR`):

| Setting           | Path | Description |
| ----------------- | ---- | ----------- |
| `CROPS`           | `crops/` | `.npy` crops named `<image_id>.npy` |
| `META`            | `hdr/` | `.hdr` metadata files (same stem) |
| `EMBEDDINGS_QWEN` | `embeddings_QWEN/` | Qwen3-VL embeddings |
| `DESCRIPTIONS`    | `image_descriptions.json` | Generated visual descriptions |

`image_id` is a string (the file stem). Canonical fields: `magnification_x`, `accelerating_voltage_kv`, `emission_current_µa`, `dwell_time_µs`, `working_distance_mm` (numeric, converted to these units), `scan_mode`, `detector` (categorical). See [`docs/indexing.md`](indexing.md) for the detector normalisation.

## Legacy test subset (`TestSem`)

`data/subset_test_1000/` with the 11 `AP_*` fields in `SETTINGS_KEYS`. Only `notebooks/test_data.ipynb` uses it. It is kept for reference.

## Thumbnails

All dataset classes define `THUMBNAIL_SIZE = (224, 224)`: the size of the downscaled (not cropped) preview stored in the Qdrant payload as `thumb_b64` and served to the chat. Reduce it (e.g. to 128×128) if payload size becomes an issue.

# Qdrant

The `Qdrant` configuration class contains the settings for the vector database.

| Setting               | Value | Description |
| --------------------- | ----- | ----------- |
| `URL`                 | `http://db-rag.dev.rd.areasciencepark.it` | Qdrant exposed through the cluster ingress; clients connect on port 80 (`storage/qdrant.py`) |
| `COLLECTION_QWEN`     | `SEM_qwen` | SEM dataset, Qwen3-VL embeddings |
| `COLLECTION_LAME`     | `LAME_qwen` | LAME dataset, Qwen3-VL embeddings |
| `COLLECTION_CLIP`     | `SEM_clip` | SEM dataset, CLIP embeddings (evaluation baseline) |
| `OLD_COLLECTION_QWEN` | `Test_OLDSEM_qwen` | Old test subset, Qwen |
| `OLD_COLLECTION_DINO` | `Test_OLDSEM_dino` | Old test subset, DINO |
| `COLLECTION_TEST`     | `Test` | Generic documents of the archived prototype / `archive/initial_rag/` |
| `EMBEDDING_DIM_QWEN`  | `4096` | |
| `EMBEDDING_DIM_DINO`  | `768`  | |
| `EMBEDDING_DIM_CLIP`  | `512`  | |

Scripts and notebooks use `URL` (outside the cluster). The deployed wrappers use the in-cluster `QDRANT_URL` instead.

# Evaluation

| Setting      | Path | Description |
| ------------ | ---- | ----------- |
| `BM25_DIR`   | `data/bm25_index/` | BM25 index over the SEM image descriptions (`scripts/index_bm25.py`) |
| `GABOR_FILE` | `data/gabor_features/gabor_features.npz` | Gabor texture features (`scripts/generate_gabor_features.py`) |


# Changing Configuration

Most project-wide settings can be changed directly in `src/sem_rag/config/settings.py`. However, changes to some settings can have consequences beyond the configuration file itself.  
For example:

### Changing an embedding model

Changing an embedding model may change the embedding dimensionality or embedding space. Existing embeddings may therefore need to be regenerated and stored in a new or recreated Qdrant collection.

### Changing a Qdrant collection

Changing a collection name may require creating or populating the corresponding collection before the retrieval pipeline can use it.

### Changing metadata fields

Adding or removing metadata fields may require corresponding changes to:
* Metadata extraction
* Qdrant payload configuration
* Retrieval filtering
* Dataset processing
* The dataset schema in `src/sem_rag/retrieval/schemas/` **and** the copy embedded in the corresponding `pipeline_wrappers/*/pipeline_wrapper.py`
* For SEM, the field dictionary CSVs

### Changing dataset paths

Changing the dataset location affects the indexing and experimentation code that relies on the configured paths.

# Configuration and Deployment

The Python configuration described in this document is used by the application code and development pipelines.  
Deployment-specific configuration is maintained separately under `k8s/`.

The Kubernetes configuration controls deployment-specific concerns such as:
* Service configuration
* Networking
* Persistent storage
* Container configuration
* Deployment values

See [`k8s/README.md`](../k8s/README.md) for Kubernetes-specific instructions.
