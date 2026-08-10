# Retrieval Pipeline

The retrieval pipeline is responsible for processing user queries, retrieving relevant SEM samples from Qdrant, and using the retrieved information as context for an LLM.

The pipeline supports both text-based and image-based queries.

## Overview

The retrieval process can be summarized as:
```text
User Query
    │
    ▼
Query Processing
    │
    ├── Text
    │
    ├── Image
    │
    ▼
Metadata Extraction
    │
    ▼
Query Embedding
    │
    ▼
Qdrant Retrieval
    │
    ▼
Retrieved SEM Samples
    │
    ▼
Context Construction
    │
    ▼
   LLM
    │
    ▼
Response
```

The retrieval pipeline is implemented using Haystack and is exposed through pipeline wrappers that can be deployed as independent services.

## Query Types

The system can receive queries in different forms.

### Text Queries

A text query describes the desired SEM samples using natural language.  
For example:
```text
Find spherical particles with a working distance of approximately 3 mm.
```

The textual query can contain both semantic information and explicit metadata constraints.  
Currently, the complete textual query is used to generate the query embedding. Therefore, metadata-related information present in the query can also influence semantic retrieval. In parallel, the retrieval pipeline extracts recognized metadata fields from the query and can use them as structured filters during the Qdrant search.  
This results in a hybrid retrieval process in which metadata can influence retrieval through both the query embedding and explicit metadata filtering.

A future improvement could be to decompose the query into separate semantic and metadata components, using only the semantic component to generate the embedding while representing metadata requirements exclusively as structured filters. This would provide a clearer separation between semantic similarity and metadata-based constraints, but would require reliable query decomposition and careful evaluation.

### Image Queries

An image can also be provided as a query.  
In this case, the image is embedded using the appropriate image embedding model and the resulting vector is used for similarity search.

Text accompanying an image can still contain useful metadata constraints. Therefore, the image is used for the semantic embedding while the textual information can be processed separately for metadata extraction.  
This separation prevents the textual query from unintentionally influencing the image embedding.

## Metadata Extraction

When the query contains metadata information, the retrieval pipeline extracts the relevant fields before performing the vector search.

The supported metadata fields are defined in the project configuration.

For each recognized field, the extractor determines the corresponding value and retrieval constraint.  
For example, a query such as:
```text
Find images with a working distance around 3 mm.
```

can be transformed into a metadata constraint on:

```text
AP_WD ≈ 3
```

The exact filtering behavior depends on the configuration of the corresponding metadata field.

Metadata extraction therefore acts as an intermediate step between the user query and the retrieval operation.

## Query Embedding

After query processing, the system generates an embedding appropriate for the query type.

For a text query:

```text
Text
 ↓
Text embedding model
 ↓
Query vector
```

For an image query:

```text
Image
 ↓
Image embedding model
 ↓
Query vector
```

> NOTE: since Qwen3-VL-Embedding-8B is multimodal, the same model is used to create both the text and image embeddings.

The query vector must belong to the same embedding space as the Qdrant collection being searched.  
For this reason, different embedding models are associated with different Qdrant collections.

## Vector Retrieval

The query embedding is used to perform a similarity search against the selected Qdrant collection.

The retrieval operation can additionally apply metadata filters extracted from the query.

Conceptually:

```text
Query vector
     │
     ├───────────────┐
     │               │
     ▼               ▼
Vector similarity   Metadata filters
     │               │
     └───────┬───────┘
             ▼
       Candidate samples
```

This allows the system to combine semantic similarity with structured SEM acquisition parameters.

## Retrieved Context

The retrieved documents contain the information required to construct the context provided to the LLM.

The retrieval system is responsible for identifying and returning the relevant candidates. The ranking itself is performed by the retrieval mechanism rather than by the LLM.  
The retrieved documents can contain:
* SEM image information
* metadata
* generated descriptions
* embeddings and associated identifiers

The retrieved information is then formatted into the prompt supplied to the language model.

## LLM Generation

After retrieval, the selected documents are provided to an LLM as contextual information.  
The LLM is instructed to answer based on the retrieved context and to avoid inventing information that is not supported by the available data.

Conceptually:

```text
Retrieved documents
        │
        ▼
Prompt construction
        │
        ▼
       LLM
        │
        ▼
Generated response
```

The LLM therefore acts primarily as the generation and interpretation component of the RAG system, while the retrieval pipeline is responsible for finding the relevant SEM samples.

## Haystack Pipeline

The retrieval workflow is implemented as a Haystack pipeline and exposed through a pipeline wrapper.

The repository currently contains multiple retrieval wrappers under:
```text
pipeline_wrappers/
├── RAG-Qwen/
└── RAG-Test/
```

These wrappers allow different retrieval configurations to be deployed and tested independently.

## Retrieval Service

The retrieval pipeline can be deployed as an independent service.

The Docker image is defined by `docker/Dockerfile.retrieval` and the corresponding Kubernetes configuration is located under `k8s/retrieval/`.

The service can therefore be deployed independently of the indexing and upload components.
