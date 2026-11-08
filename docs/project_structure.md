# Project Structure

This document describes the organization of the InternRAG repository.

The repository is divided into different components according to their purpose:

- Deployment configuration
- Experimentation
- Reusable source code
- Service implementations

## Directory Overview

```text
.
├── archive/
├── data/             # not versioned
├── docker/
├── docs/
├── k8s/
├── notebooks/
├── pipeline_wrappers/
├── render/
└── src/
```

# archive/

`archive/initial_rag/` contains the first generic document-RAG prototype: the Docling-based indexing wrapper and the `RAG-Test` retrieval wrapper, the upload web UI, their Dockerfiles and Kubernetes manifests, and early notebooks. It is not part of the current system.

# data/

Not versioned. Holds the datasets (`SEM/`, `LAME/`, `LAME_filtered/`, `subset_test_1000/`), generated embeddings/descriptions, baseline indexes (`bm25_index/`, `gabor_features/`) and evaluation outputs (`evaluation/`).

# docker/

Contains `Dockerfile.retrieval`, which packages `render/app.py` and the `RAG-Qwen` and `RAG-LAME` pipeline wrappers into a Hayhooks service. See [`docker/README.md`](../docker/README.md).

# k8s/

Contains Kubernetes deployment configurations.  
Moreover, it contains a README file containing explanation of the different deployments.

The directory includes configurations for:

* The retrieval service (`retrieval/`)
* Qdrant (`qdrant/`)
* Open WebUI (`open_webui/`)
* The shared `rag-config` ConfigMap (`config.yaml`)
* Debugging utilities (`net_debug/`, `hello_world/`)

`keycloak/` is kept from an earlier attempt at SSO but is not currently used.

Each service contains its own deployment configuration or Helm values.

# notebooks/

Contains experimental notebooks used during development, such as:

* Data preparation: `lame_images.ipynb` (LAME filtering/cropping), `embed.ipynb`, `qdrant_upload.ipynb`
* Analysis: `metadata_analysis.ipynb`, `qdrant_analysis.ipynb`, `descriptions_analysis.ipynb`, `retrieval_analysis.ipynb`, `test_data.ipynb`
* Evaluation: `EVAL_text_retrieval.ipynb`, `EVAL_image_retrieval.ipynb`, `EVAL_metadata_extraction.ipynb`, `EVAL_end2end.ipynb` (see [`docs/evaluation.md`](docs/evaluation.md))

Notebooks are mainly intended for experimentation and debugging rather than production execution.

# pipeline_wrappers/

Contains wrappers exposing Haystack pipelines as deployable services.

Each subdirectory corresponds to a different pipeline implementation:

```text
pipeline_wrappers/
├── RAG-Qwen/   # SEM dataset (collection SEM_qwen)
├── RAG-LAME/   # LAME dataset (collection LAME_qwen)
```

Each wrapper is self-contained (it does not import `sem_rag`), because the Docker image does not install the package. The reusable versions of its components live in `src/sem_rag/retrieval/` and must be kept in sync by hand.

> [!NOTE]
> In OpenWebUI, the model takes the name of the subdirectory (e.g. RAG-Qwen).

# render/

`render/app.py` is the entry point of the retrieval service. It creates the Hayhooks FastAPI app (which auto-deploys every wrapper under `HAYHOOKS_PIPELINES_DIR`) and adds two thumbnail endpoints:

* `GET /rag-images/{image_id}.png`: thumbnail from `SEM_qwen` (looked up by `meta.SEMImageID`)
* `GET /rag-images-lame/{image_id}.png`: thumbnail from `LAME_qwen` (looked up by `meta.image_id`)

# src/

Contains the main Python package.

The project follows a standard Python package layout:

```text
src/sem_rag/
├── config/settings.py      # paths, models, datasets, Qdrant, evaluation paths
├── dataset/
│   ├── loader.py           # SEM: JSON metadata → canonical fields, embeddings loader, payload indexes
│   ├── metadata.py         # SEM: value/unit, pixel size, magnification and category parsers
│   ├── loader_lame.py      # LAME: .hdr metadata → DataFrame, drops multi-detector images, payload indexes
│   └── metadata_lame.py    # LAME: .hdr field map, unit conversion, TE* → STEM detector normalisation
├── embedding/embedder.py   # QwenEmbedder (vLLM) and CLIPEmbedder
├── image/
│   ├── descriptions.py     # VLM image descriptions (cached in image_descriptions.json), crop lookup
│   └── encoding.py         # .npy crop → PNG data URL / thumbnail
├── retrieval/
│   ├── components.py       # QueryMetadataExtractor, QueryEmbedder, MMRReranker (Haystack components)
│   ├── schemas/sem.py      # SEM metadata schema + extraction system prompt
│   ├── schemas/lame.py     # LAME metadata schema + extraction system prompt
│   ├── bm25.py             # BM25 baseline over image descriptions
│   └── gabor.py            # Gabor texture-feature baseline
├── scripts/                # CLI entry points (embeddings, Qdrant upload, baselines)
└── storage/qdrant.py       # get_document_store() for the project Qdrant instance
```

The package contains reusable code shared across different parts of the project.

# pyproject.toml / uv.lock

Define the `sem-rag` package and its dependencies (managed with uv); `uv sync` sets up the environment. `requirements.txt` is a minimal list used mainly for Docker images.

# README.md

Provides a high-level introduction and quick-start instructions.  
Detailed documentation is maintained inside the `docs/` directory.
