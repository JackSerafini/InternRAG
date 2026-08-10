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
├── docker/
├── k8s/
├── notebooks/
├── pipeline_wrappers/
├── render/
├── src/
└── upload/
```

# docker/

Contains the Dockerfiles used to package the different services.

Current Docker images include:
* Indexing service
* Retrieval service
* Upload interface

The images are built for deployment in Kubernetes environments.

# k8s/

Contains Kubernetes deployment configurations.  
Moreover, it contains a README file containing explanation of the different deployments.

The directory includes configurations for:
* Application services
* Qdrant
* Open WebUI
* Keycloak
* Networking components

Each service contains its own deployment configuration or Helm values.

# notebooks/

Contains experimental notebooks used during development.

Examples of tasks performed through notebooks:
* Generating embeddings
* Uploading data to Qdrant
* Evaluating retrieval performance
* Testing RAG pipelines
* Inspecting datasets

Notebooks are mainly intended for experimentation and debugging rather than production execution.

# pipeline_wrappers/

Contains wrappers exposing Haystack pipelines as deployable services.

Each subdirectory corresponds to a different pipeline implementation:
```text
pipeline_wrappers/
├── indexing/
├── RAG-Qwen/
└── RAG-Test/
```

> NOTE: in OpenWebUI, the model takes the name of the subdirectory (e.g. RAG-Qwen).

These wrappers allow pipelines to be executed through the deployment infrastructure.

# render/

Contains rendering-related utilities.

Currently, this directory contains the application entry point used for rendering SEM images.

# src/

Contains the main Python package.

The project follows a standard Python package layout:
```text
src/
└── sem_rag/
    ├── config/
    ├── utils/
    └── qdrant_upload.py
```

The package contains reusable code shared across different parts of the project.

## src/sem_rag/config/

Contains centralized project configuration.

Examples:
* Model configuration
* Paths
* Qdrant settings
* Metadata fields

Keeping configuration centralized avoids duplicating parameters across scripts and services.

## src/sem_rag/utils/

Contains shared utility functions used throughout the project.

> NOTE: right now, no utility functions have been created.

# upload/

Contains the upload service.

The service provides a user-facing interface for submitting new data into the system.

Structure:
```text
upload/
├── main.py
└── static/
    └── index.html
```

# requirements.txt

Contains the Python dependencies required by the project.  
It represents the main source of truth for Python environment setup.

# README.md

Provides a high-level introduction and quick-start instructions.  
Detailed documentation is maintained inside the `docs/` directory.
