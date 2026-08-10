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

| Variable       | Description                                       |
| -------------- | ------------------------------------------------- |
| `HF_TOKEN`     | Hugging Face authentication token                 |
| `VLLM_API_KEY` | API key used to authenticate with the vLLM server |
| `VLLM_API_URL` | Base URL of the vLLM API                          |

`VLLM_API_URL` has a default value pointing to the project's remote vLLM server. It can be overridden through the environment when using a different deployment.

Sensitive values such as `HF_TOKEN` and `VLLM_API_KEY` should **not** be committed to the repository.

A local `.env` file can be used during development:
```text
HF_TOKEN=your_huggingface_token
VLLM_API_KEY=your_api_key
VLLM_API_URL=http://localhost:8000/v1
```

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
| `API_KEY`         | Environment variable           | Authentication for the vLLM API            |
| `API_URL`         | Environment variable / default | Base URL of the vLLM OpenAI-compatible API |
| `GEMMA_MODEL`     | `google/gemma-4-26B-A4B-it`    | Gemma model used by the application        |
| `GPTOSS_MODEL`    | `openai/gpt-oss-120b`          | GPT-OSS model used by the application      |
| `EMBEDDING_MODEL` | `Qwen/Qwen3-VL-Embedding-8B`   | Multimodal embedding model                 |

The model names are kept in configuration so that model selection can be changed without modifying the pipeline implementation.

# Test SEM Dataset

The `TestSem` configuration class contains paths and parameters associated with the current test dataset.  
The dataset is located under `data/subset_test_1000/`.  
Its relevant subdirectories and files are:

| Setting           | Path                      | Description                         |
| ----------------- | ------------------------- | ----------------------------------- |
| `CROPS`           | `crops/`                  | SEM image crops                     |
| `JSON`            | `json/`                   | Metadata associated with the images |
| `EMBEDDINGS_DINO` | `embeddings/`             | DINO embeddings                     |
| `EMBEDDINGS_QWEN` | `embeddings_QWEN/`        | Qwen embeddings                     |
| `DESCRIPTIONS`    | `image_descriptions.json` | Generated image descriptions        |

The dataset-specific configuration is currently named `TestSem` because these paths correspond to the test dataset used during development and evaluation.

### Thumbnail Configuration

`THUMBNAIL_SIZE` defines the resolution used when generating image previews for chat rendering:

```python
THUMBNAIL_SIZE = (224, 224)
```

This does not crop the original image. It creates a smaller preview while preserving the full field of view.  
If the size of the data sent to the chat interface becomes an issue, the resolution can be reduced.

### SEM Metadata

`SETTINGS_KEYS` defines the SEM acquisition parameters that are extracted and made available to the retrieval system.  
Currently, the fields are:

```text
AP_WD
AP_FREE_WD
AP_BEAM_TIME
AP_STAGE_LOW_Z
AP_STAGE_CENTRE_X
AP_C3
AP_EHT_CAL_30KV
AP_EHT_CAL_10KV
AP_EHT_CAL_100
AP_EHT_CAL_24KV
AP_MINMAG
```

These parameters represent microscope and acquisition settings associated with each SEM image.

The fields are used when constructing document metadata and when processing metadata-related query constraints.

The exact interpretation and filtering behavior of these fields is defined by the metadata extraction and retrieval logic rather than by the field list itself.

# Qdrant

The `Qdrant` configuration class contains the settings for the vector database.

| Setting              | Value                   | Description                           |
| -------------------- | ----------------------- | ------------------------------------- |
| `URL`                | `http://localhost:6333` | Qdrant server URL                     |
| `COLLECTION_QWEN`    | `SEMImages_qwen`        | Collection containing Qwen embeddings |
| `COLLECTION_DINO`    | `SEMImages_dino`        | Collection containing DINO embeddings |
| `COLLECTION_TEST`    | `Test`                  | Test collection                       |
| `EMBEDDING_DIM_QWEN` | `4096`                  | Dimensionality of Qwen embeddings     |
| `EMBEDDING_DIM_DINO` | `768`                   | Dimensionality of DINO embeddings     |

Different embedding models are stored in separate Qdrant collections because their vectors belong to different embedding spaces and can have different dimensionalities.  
For example:

```text
Qwen embedding -> SEMImages_qwen -> dimension: 4096

DINO embedding -> SEMImages_dino -> dimension: 768
```

The configured embedding dimension must match the dimensionality expected by the corresponding Qdrant collection.

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
