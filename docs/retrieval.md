# Retrieval Pipeline

The retrieval pipeline processes a user query, retrieves the most relevant images from Qdrant and uses them as context for an LLM, which describes the candidates to the researcher.

It is built from [Haystack](https://haystack.deepset.ai/) pipelines wrapped as [Hayhooks](https://github.com/deepset-ai/hayhooks) pipeline wrappers. Each wrapper is exposed as an OpenAI-compatible model and appears in Open WebUI under its directory name.

| Pipeline | Dataset | Collection | Thumbnail endpoint |
| -------- | ------- | ---------- | ------------------ |
| `RAG-Qwen` | SEM | `SEM_qwen` | `/rag-images` |
| `RAG-LAME` | LAME | `LAME_qwen` | `/rag-images-lame` |

Both wrappers have the same architecture. They differ only in the collection, the metadata schema, the answer format and the thumbnail endpoint, so this document describes them together. An earlier generic pipeline, `RAG-Test`, is archived in `archive/initial_rag/`.

## Overview

```text
                 User message
                      │
        ┌─────────────┴─────────────┐
        │                           │
   image (if any)                  text
    or text only                    │
        │                           ▼
        ▼                 QueryMetadataExtractor
  QueryEmbedder                 (Gemma 4)
(Qwen3-VL-Embedding)                │
        │                           ▼
        │                     Qdrant filters
        └─────────────┬─────────────┘
                      ▼
        QdrantEmbeddingRetriever (top 50)
                      │
                      ▼
                MMRReranker (top 5)
                      │
                      ▼
        ChatPromptBuilder → Gemma 4 → answer
                      │
                      ▼
        answer + "Candidate images" gallery
```

**Query embedding and metadata extraction are independent.** Both run on the same user message, and their outputs (a vector and a filter) are combined only at the Qdrant retriever.

## Query Types

The wrapper takes the **last user message** of the OpenAI-style request. It concatenates all of its text parts and collects its `image_url` parts.

### Text Queries

```text
Find spherical particles with a working distance of approximately 3 mm.
```

The text is used twice:

1. **Embedding.** The whole text is embedded by `Qwen/Qwen3-VL-Embedding-8B`, so the metadata wording ("3 mm") also influences the vector.
2. **Metadata extraction.** The same text goes to the `QueryMetadataExtractor`, which turns the explicit constraints into a filter, here `working_distance_mm` between 2.7 and 3.3.

As a result, metadata currently affects retrieval in two ways: through the query embedding and through the filter. A possible improvement is to remove the metadata part of the query before embedding it, so that constraints act only through filters. That would require a reliable query decomposition step and a dedicated evaluation.

### Image Queries

```text
[image] Find images similar to this one, with a working distance around 3 mm.
```

When the message contains an image:

* Only the **first** image is embedded, and the text is **not** included in the embedding
* The text still goes to the metadata extractor

The image therefore drives visual similarity, while the text only contributes metadata filters.

## Query Embedding

`QueryEmbedder` calls the vLLM `/embeddings` endpoint with `Qwen/Qwen3-VL-Embedding-8B` (4096-d). The call uses a chat-style message with the instruction `"Represent the user's input."`, followed by either the image (as a data URL) or the text. Images in the collections were embedded with the same model, so text and image queries share one embedding space.

## Metadata Extraction

`QueryMetadataExtractor` sends the query and a JSON **metadata schema** to `google/gemma-4-26B-A4B-it` in JSON mode, then validates the answer in Python.

For every canonical field, the schema lists:

* Its type and a scientific description
* `dictionary_terms`, i.e. aliases the user may use
* The unit (numeric fields) or allowed values, each with its own aliases (categorical fields)
* A `filter` entry with the tolerance used for approximate values

This lets the model map "EHT", "beam voltage" or "kV" to `accelerating_voltage_kv`, or "TE bright field" to `detector == "STEM"`, without the user knowing the field names. The model is told to extract only explicitly stated constraints, never to infer metadata from morphology or general knowledge, and to return `{}` when there are none.

| Pipeline | Numeric fields | Categorical fields |
| -------- | -------------- | ------------------ |
| `RAG-Qwen` | `pixel_size_nm`, `magnification_x`, `accelerating_voltage_kv`, `working_distance_mm`, `brightness_percent`, `contrast_percent`, `scan_speed_setting`, `frame_average_count`, `line_average_count` | `category` (`Porous_Sponge`, `Patterned_surface`, `Particles`, `Films_Coated_Surface`, `Powder`, `Tips`, `Nanowires`, `Biological`, `MEMS_devices_and_electrodes`, `Fibres`), `detector` (`InLens`, `SE2`, `HDAsB`) |
| `RAG-LAME` | `magnification_x`, `accelerating_voltage_kv`, `emission_current_µa`, `dwell_time_µs`, `working_distance_mm` | `scan_mode` (`ANALYSIS`, `UH-RESOLUTION`, `WIDE FIELD`), `detector` (`Axial`, `Axial (BSE)`, `E-T`, `LE BSE`, `MD`, `STEM`) |

### Operators

The model returns, for each field, an object `{"operator": ..., "value": ...}`:

| Operator | Field type | Filter |
| -------- | ---------- | ------ |
| `>=`, `<=` | numeric | the same comparison |
| `~` | numeric | range `value ± tolerance` (also used for a bare target value such as "at 5 kV") |
| `between` | numeric | range `[low, high]` |
| `==` | categorical | exact match on one allowed value |

Examples:

```text
"accelerating voltage above 10 kV"     → accelerating_voltage_kv >= 10
"working distance around 8 mm"         → 7.2 <= working_distance_mm <= 8.8
"InLens images of nanowires"           → detector == "InLens" AND category == "Nanowires"
```

### Tolerance

The tolerance for `~` is read from each field's `filter` entry (`tolerance`, `tolerance_type`). With `relative`, the range is `value ± value × tolerance`; with any other type, `tolerance` is an absolute amount. **All fields currently use a 10 % relative tolerance.** For small values this is almost an exact match, so some fields may need an absolute tolerance in the future.

### Validation and Filter Construction

The extractor never queries Qdrant directly. It outputs a Haystack filter that is connected to the `filters` input of `QdrantEmbeddingRetriever`. Each constraint is checked in Python. A constraint is **discarded** when:

* Its field is not in the schema
* Its operator is not supported for that field type
* Its value is not numeric (numeric fields), or `between` does not have exactly two numeric bounds
* Its categorical value is not one of the allowed values

Reversed `between` bounds are swapped. The remaining constraints are combined with `AND` on the `meta.<field>` payload keys. If nothing valid remains, or the LLM output cannot be parsed, **no filter is applied** and retrieval is purely by similarity.

If the filter is so strict that Qdrant returns nothing, the wrapper skips generation and replies with a fixed message:

* `RAG-Qwen`: "I couldn't find any SEM images matching all the requested criteria."
* `RAG-LAME`: "I couldn't find any SEM images matching the query and its metadata constraints."

## Vector Retrieval and MMR

`QdrantEmbeddingRetriever` (cosine similarity) receives the query embedding and the filters and returns the **top 50** candidates (`MMR_CANDIDATES`) together with their embeddings.

`MMRReranker` reduces them to **5** (`TOP_K`) with Maximal Marginal Relevance, using `λ = 0.8`:

$$ \text{MMR}(d) = \lambda \cdot \text{sim}(\text{query}, d) - (1 - \lambda) \cdot \max_{s \in \text{selected}} \text{sim}(d, s) $$

The first pick is the image most similar to the query. Each following pick balances similarity to the query against similarity to the images already chosen. This avoids returning five near-identical images from the same acquisition session. If 5 or fewer candidates pass the filter, they are returned as they are.

**Ranking is done entirely by the retrieval system.** The LLM never decides which image is more relevant.

## Prompt Construction and Generation

Each retrieved `Document` carries:

* `content`: the metadata line plus the visual description written at indexing time (see [indexing.md](indexing.md));
* `meta`: the canonical fields, the identifier and the `thumb_b64` thumbnail;
* `embedding`: used only by the MMR step.

`ChatPromptBuilder` inserts the user query and the `content` of each of the 5 candidates into the prompt, and `VLLMChatGenerator` sends it to `google/gemma-4-26B-A4B-it`. The system prompt tells the model that the candidates have already been ranked, and that it must:

* Write one block per candidate, in a fixed format
* Describe the morphology using only the stored visual description
* Report the metadata fields in a fixed order, writing "Not available" for missing ones
* Keep stored values and units unchanged, and not infer, estimate or normalise them
* Not rank, score or compare candidates, and not use external knowledge

Output format per candidate:

```text
**Image <ID>**

**Morphology:** <brief description>

**Metadata:** <field>: <value> | <field>: <value> | …
```

| Pipeline | Metadata fields, in order |
| -------- | ------------------------- |
| `RAG-Qwen` | Category, Detector, Pixel size, Magnification, Accelerating voltage, Working distance, Brightness, Contrast, Scan Speed, Frame Average, Line Average |
| `RAG-LAME` | Magnification, Accelerating voltage, Emission current, Dwell time, Working distance, Scan mode, Detector |

## Image Gallery

After the answer, the wrapper appends a **"Candidate images"** gallery: a numbered list with each image ID and a Markdown image that points to the thumbnail endpoint.

| Pipeline | Thumbnail URL | Qdrant lookup |
| -------- | ------------- | ------------- |
| `RAG-Qwen` | `{THUMBNAIL_BASE_URL}/{id}.png`, default `https://llm-rag.dev.rd.areasciencepark.it/rag-images` | `SEM_qwen`, `meta.SEMImageID` |
| `RAG-LAME` | `https://llm-rag.dev.rd.areasciencepark.it/rag-images-lame/{id}.png` (hard-coded) | `LAME_qwen`, `meta.image_id` |

The endpoints are defined in `render/app.py`, which is the retrieval service's entry point (see [Deployment](#deployment)). They read the `thumb_b64` payload field of the matching point, decode it and return a PNG (404 if not found). The Open WebUI ingress (`k8s/open_webui/ingress.yaml`) routes `/rag-images` and `/rag-images-lame` to the retrieval service, so the browser loads the thumbnails from the same host as Open WebUI.

```text
Retrieved document ─► image ID ─► /rag-images/{id}.png ─► Qdrant (thumb_b64) ─► PNG ─► Open WebUI
```

## Streaming

Retrieval always runs synchronously first, so a zero-result query can be answered before the LLM is called. After that:

* **`stream=true`**: Hayhooks' `streaming_generator` streams the Gemma answer token by token, and the gallery is appended when generation ends (`on_pipeline_end`).
* **`stream=false`**: the generation pipeline runs to completion and the answer is returned with the gallery appended.

## Haystack Pipelines

Each wrapper builds **two** pipelines in `setup()`.

Retrieval pipeline:

```text
QueryEmbedder ──embedding──► QdrantEmbeddingRetriever (top_k=50) ──documents──► MMRReranker (top_k=5)
      │                              ▲ filters                                       ▲
      │                              │                                               │
      └──────────────embedding───────┼───────────────────────────────────────────────┘
                                     │                               (query_embedding)
QueryMetadataExtractor ──────────────┘
```

Generation pipeline:

```text
ChatPromptBuilder ──► VLLMChatGenerator (Gemma 4) ──► AnswerBuilder
```

`run_chat_completion()` extracts the query, runs the retrieval pipeline, handles the zero-result case, and then runs the generation pipeline (streamed or not).

### Where the code lives

The components (`QueryMetadataExtractor`, `QueryEmbedder`, `MMRReranker`), the metadata schema and the prompts are defined **inline in each wrapper**, because the Docker image does not install the `sem_rag` package.

The notebooks and evaluations use the same logic from the package:

* `src/sem_rag/retrieval/components.py`: the components, parameterised by schema and system prompt
* `src/sem_rag/retrieval/schemas/sem.py` and `lame.py`: `METADATA_SCHEMA` and `EXTRACTION_SYSTEM_PROMPT`

**Any change to a component, schema or prompt must be applied in both places.**

### Configuration

| Variable | Used by | Default |
| -------- | ------- | ------- |
| `VLLM_API_KEY` | both wrappers | none (from the `vllm-api-key` secret) |
| `VLLM_API_URL` | both wrappers | `https://orfeo-llm.areasciencepark.it/vllm/v1` |
| `QDRANT_URL` | both wrappers, `render/app.py` | `http://qdrant.orfeo-rag.svc.cluster.local:6333` (set by the `rag-config` ConfigMap) |

Model names, `MMR_CANDIDATES`, `TOP_K`, λ and the collection name are constants at the top of each wrapper.

## Deployment

The retrieval service image is built from `docker/Dockerfile.retrieval`:

```text
/srv
├── app.py                          # render/app.py
└── pipeline_wrappers/
    ├── RAG-Qwen/pipeline_wrapper.py
    └── RAG-LAME/pipeline_wrapper.py
```

The container runs `uvicorn app:hayhooks` on port 1416. `render/app.py` creates the Hayhooks FastAPI app with `create_app()`, so at startup Hayhooks still auto-deploys every wrapper found in `HAYHOOKS_PIPELINES_DIR` (`/srv/pipeline_wrappers`). The same app also serves the thumbnail endpoints. One service therefore exposes all pipelines (as OpenAI-compatible models under `/v1`) plus the thumbnails.

The Kubernetes manifests are in `k8s/retrieval/`. Build and deployment steps are in [docker/README.md](../docker/README.md) and [k8s/README.md](../k8s/README.md).
