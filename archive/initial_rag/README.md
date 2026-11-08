# Initial RAG Prototype

This directory contains the first, generic RAG system built at the start of the project, before the SEM-specific system existed.
Users uploaded documents through a small web UI. An indexing service split them into chunks with Docling, embedded them and stored them in the `Test` Qdrant collection, and a retrieval pipeline answered questions over that collection.

It is **not part of the current system**. It is kept as a reference for reusing the generic document-indexing approach in future, general-purpose RAG projects. It is not deployed and may not work with the current dependencies.

## Architecture

```text
Browser
   │  upload (PDF, DOCX, PPTX, HTML, Markdown, TXT)
   ▼
Upload service (FastAPI, port 7860)
   │  POST /indexing/run
   ▼
Indexing service (Hayhooks, port 1416)
   │  DoclingConverter → chunks → Qwen3-VL embeddings
   ▼
Qdrant collection "Test"
   ▲
   │  top-k retrieval
RAG-Test pipeline (Hayhooks) ──► Qwen/Qwen3.5-9B ──► answer in Open WebUI
```

## Contents

```text
initial_rag/
├── docker/
│   ├── Dockerfile.indexing     # Hayhooks + docling-haystack, serves pipeline_wrappers/indexing
│   └── Dockerfile.upload       # FastAPI upload UI
├── k8s/
│   ├── indexing/               # Deployment + Service, port 1416
│   └── upload/                 # Deployment + Service, port 7860
├── notebooks/
│   ├── rag.ipynb               # first indexing + RAG experiments
│   ├── test.ipynb              # indexing + RAG tests
│   └── evaluation.ipynb        # indexing a prepared dataset and evaluating the pipeline with Haystack
├── pipeline_wrappers/
│   ├── indexing/               # Docling → Qwen3-VL-Embedding-8B → Qdrant "Test"
│   └── RAG-Test/               # retrieval over "Test", generation with Qwen/Qwen3.5-9B
└── upload/
    ├── main.py                 # forwards uploads to the indexing service
    └── static/index.html
```

## Components

### Indexing (`pipeline_wrappers/indexing/`)

Hayhooks wrapper that converts an uploaded file into chunks with `DoclingConverter` (`ExportType.DOC_CHUNKS`), embeds them with `Qwen/Qwen3-VL-Embedding-8B` through the vLLM gateway, and writes them to the `Test` collection.
It reads `VLLM_API_KEY`, `VLLM_API_URL` and `QDRANT_URL` from the environment.

### Upload UI (`upload/`)

Minimal FastAPI app that serves an upload page and forwards each file to the indexing service at `INDEXING_SERVICE_URL` (default `http://rag-indexing.orfeo-rag.svc.cluster.local:1416`). It also exposes `/health`.

### RAG-Test (`pipeline_wrappers/RAG-Test/`)

Hayhooks retrieval wrapper over the `Test` collection: it embeds the query with `Qwen/Qwen3-VL-Embedding-8B`, retrieves from Qdrant and generates the answer with `Qwen/Qwen3.5-9B`. It used to be served by the main retrieval image and appeared in Open WebUI as the `RAG-Test` model.

## Building and deploying (historical)

The Dockerfiles use paths relative to this directory, so build them from `archive/initial_rag/`:

```bash
docker buildx build --platform linux/amd64 -t <dockerhub-user>/rag-indexing:<tag> -f docker/Dockerfile.indexing --push .
docker buildx build --platform linux/amd64 -t <dockerhub-user>/rag-upload:<tag> -f docker/Dockerfile.upload --push .
```

The services were deployed in the `orfeo-rag` namespace. As in the main `k8s/` directory, `values.yaml` files are Deployment manifests, not Helm values. The indexing service uses the shared `rag-config` ConfigMap and the `vllm-api-key` secret:

```bash
kubectl apply -f k8s/indexing/
kubectl apply -f k8s/upload/
```

`RAG-Test` has no Dockerfile of its own here. To serve it again, copy it into a Hayhooks image (for example by adding it to `docker/Dockerfile.retrieval` in the repository root).

## Notes

* The notebooks were written when they lived in the top-level `notebooks/` folder. Their import cell (`Path.cwd().parent / "src"`) no longer points to the `sem_rag` package from here, so fix that path before running them.
* The `Test` collection may or may not still exist in Qdrant.
