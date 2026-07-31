# InternRAG

InternRAG is a Retrieval-Augmented Generation (RAG) system developed for the retrieval and analysis of **Scanning Electron Microscopy (SEM)** data. The project combines multimodal retrieval, metadata filtering, and Large Language Models (LLMs) to enable researchers to search and explore SEM datasets using both natural language and image queries.

The system is designed around a modular architecture consisting of separate indexing, retrieval, and upload services, making it suitable for experimentation as well as deployment in Kubernetes environments.

## Features

* Multimodal retrieval over SEM datasets
* Image and text-based search
* Automatic document and metadata indexing
* LLM-powered Retrieval-Augmented Generation
* Qdrant vector database integration
* Kubernetes deployment with Helm
* Keycloak authentication support
* Open WebUI integration

## Project Structure

```
.
├── docker/              # Dockerfiles for each service
├── k8s/                 # Kubernetes and Helm configuration
├── notebooks/           # Experiments and development notebooks
├── pipeline_wrappers/   # Hayhooks pipeline wrappers
├── render/              # Rendering utilities
├── src/
│   └── sem_rag/         # Core Python package
└── upload/              # Upload web interface
```

A more detailed explanation of the repository structure is available in the project documentation.

# Architecture

InternRAG is organized into three main components:

### 1. Indexing

Responsible for preparing the knowledge base.

The indexing pipeline:

* Loads SEM images and metadata
* Extracts textual information from the crops
* Generates embeddings
* Creates Haystack documents from embeddings and metadata
* Uploads everything into Qdrant

### 2. Retrieval

Handles user queries.

Given either a text query or an image, the retrieval service:

* Generates the appropriate embedding
* Performs metadata extraction from the query
* Performs metadata filtering on the database
* Retrieves relevant documents from Qdrant
* Builds the RAG context
* Generates a response using an LLM

### 3. Upload

Provides a web interface for uploading new datasets into the system, enabling new documents to be indexed without directly interacting with the backend.

# Installation

## Requirements

* Python 3.12
* Git
* Docker (optional)
* Kubernetes + Helm (optional for deployment)

### Linux

Create a virtual environment and install the dependencies:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If additional packages are required during development, install them as needed.

### macOS

Install the Metal version of vLLM:

```bash
curl -fsSL https://raw.githubusercontent.com/vllm-project/vllm-metal/main/install.sh | bash
source ~/.venv-vllm-metal/bin/activate
pip install -r requirements.txt
```

For Apple Silicon devices, refer to the official vLLM Metal repository for supported models and installation details (https://github.com/vllm-project/vllm-metal).

# Docker

Three Docker images are provided.

| Service   | Dockerfile                    | Purpose                         |
| --------- | ----------------------------- | ------------------------------- |
| Indexing  | `docker/Dockerfile.indexing`  | Builds the indexing service     |
| Retrieval | `docker/Dockerfile.retrieval` | Builds the retrieval service    |
| Upload    | `docker/Dockerfile.upload`    | Builds the upload web interface |

Example:

```bash
docker buildx build \
    --platform linux/amd64 \
    -t your-dockerhub-user/rag-retrieval:latest \
    -f docker/Dockerfile.retrieval \
    --push .
```

Equivalent commands can be used for the indexing and upload services by changing the Dockerfile and image name.

# Kubernetes

Deployment manifests and Helm values are located in the `k8s/` directory.

The repository contains configurations for:

* Qdrant
* Retrieval service
* Indexing service
* Upload service
* Open WebUI
* Keycloak

Refer to the Kubernetes documentation for deployment instructions.

# Notebooks

The `notebooks/` directory contains experiments and development utilities, including:

* Embedding generation
* Qdrant upload
* Retrieval evaluation
* RAG prototyping
* Dataset inspection
* Testing

These notebooks are intended for development and experimentation rather than production use.

# Documentation

Additional documentation is being developed and will cover:

* System architecture
* Retrieval pipeline
* Indexing pipeline
* Kubernetes deployment
* Configuration
* Developer guide

# License

This project is distributed under the MIT License. See the `LICENSE` file for details.
