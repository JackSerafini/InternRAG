# Indexing Pipeline

The indexing pipeline is responsible for transforming the SEM and LAME dataset into a searchable representation stored in Qdrant.

There are two indexing-related systems in the repository:

1. **Generic document indexing prototype**: archived in `archive/initial_rag/` (Docling-based indexing wrapper + upload UI). It is not part of the current system.
2. **SEM dataset indexing**: implemented by the scripts in `src/sem_rag/scripts/` on top of the `sem_rag` package. This document covers this one. It indexes two static datasets: **SEM** (collection `SEM_qwen`) and **LAME** (collection `LAME_qwen`).

## Overview

The SEM indexing process can be summarized as:

```text
        SEM Dataset
             │
     ┌───────┴───────┐
     │               │
   Images         Metadata
     │               │
     ▼               ▼
Embeddings     Metadata Processing
     │               │
     └───────┬───────┘
             │
             ▼
     Haystack Documents
             │
             ▼
          Qdrant
```

The main stages are:

1. Prepare crops (SEM: already in data/SEM/crops; LAME: lame_images.ipynb)
2. Generate Qwen3-VL image embeddings
3. Normalise metadata to canonical fields
4. Get or generate a visual description per image (Gemma 4)
5. Build Haystack Documents (text content + embedding + payload + thumbnail)
6. Recreate the collection and write the documents to Qdrant

The implementation lives in `src/sem_rag/` (dataset loaders, embedding, descriptions) and is driven by the CLI scripts in `src/sem_rag/scripts/`.

## Input Data

| Dataset | Images | Metadata | Identifier |
| ------- | ------ | -------- | ---------- |
| SEM  | `data/SEM/crops/<SEMImageID>_*.npy` | one JSON per image (`data/SEM/json/`), mapped to canonical fields through the field-dictionary CSVs; `category` from `filtered_categories.csv` | `SEMImageID` (int) |
| LAME | `data/LAME_filtered/crops/<image_id>.npy` (produced by `notebooks/lame_images.ipynb`) | one `.hdr` (INI) file per image in `data/LAME_filtered/hdr/` | `image_id` (str, file stem) |

Both datasets are treated as **static knowledge bases**: re-indexing recreates the collection.

## Image Embeddings

Each crop is embedded with `Qwen/Qwen3-VL-Embedding-8B` (4096-d) through the vLLM gateway (`embedding/embedder.py`, `QwenEmbedder`), one `.pt` file per image. CLIP (512-d) embeddings of the SEM dataset are also generated for the evaluation baseline (`SEM_clip`). DINO embeddings were only used in earlier experiments.

## Metadata Processing

The metadata is normalised to **canonical fields** with fixed units:

* **SEM** (`dataset/loader.py`, `dataset/metadata.py`): `pixel_size_nm`, `magnification_x`, `accelerating_voltage_kv`, `working_distance_mm`, `brightness_percent`, `contrast_percent`, `scan_speed_setting`, `frame_average_count`, `line_average_count`, plus categorical `category` and `detector`. Values are parsed together with their units; pixel size is normalised to nm and magnification to a plain factor (`X`).
* **LAME** (`dataset/metadata_lame.py`, `dataset/loader_lame.py`): `magnification_x`, `accelerating_voltage_kv` (V→kV), `emission_current_µa` (A→µA), `dwell_time_µs` (s→µs), `working_distance_mm` (m→mm), plus categorical `scan_mode` and `detector`.

Missing or unparsable values are stored as `None` and omitted from the payload.

### LAME detector normalisation

LAME images record the detector as a free string. Two rules are applied at upload time:

1. **All transmitted-electron channels are merged into `STEM`.** Any detector value whose first token is `TE` (`TE BF`, `TE DF`, `TE DF #2`, `TE HADF`, …) is stored as `STEM` (`normalize_detector()`). The metadata schema lists these channel names as aliases of `STEM`, so a query such as "TE bright field" is mapped to `detector == "STEM"`.
2. **Images acquired with multiple detectors are discarded.** Rows whose detector value contains a comma (e.g. `Axial, MD, E-T`) are dropped in `load_all_metadata()` and are not uploaded.

## Haystack Documents

The indexed samples are represented as Haystack `Document` objects before being uploaded to Qdrant.

Conceptually, each document contains:

```text
Document
├── id            # str(SEMImageID) or image_id
├── content       # "SEM image <id>. <field>: <value> <unit>. …" + "\n\nVisual description:\n<description>"
├── embedding     # Qwen3-VL image embedding
└── meta
    ├── SEMImageID, ImageOriginalName, ImageHashName   (SEM)  |  image_id  (LAME)
    ├── <canonical numeric fields>    (float)
    ├── <canonical categorical fields> (str)
    └── thumb_b64                     # 224×224 PNG data URL served by render/app.py
```

The visual description is generated once per image by a vision-language model (`google/gemma-4-26B-A4B-it`) through vLLM (`image/descriptions.py`) and cached in the dataset's `image_descriptions.json`. Missing descriptions are generated on demand during upload. The description is what the generation LLM later uses to describe the morphology of a candidate.

The textual content provides a human-readable representation of the indexed sample, while the embedding and structured metadata are used by the retrieval system.

## Qdrant

Qdrant is used as the vector database for the indexed SEM dataset.

For each indexed sample, the image embedding is stored as the vector representation and the associated metadata is stored as payload.

Each embedding space has its own collection, because vectors of different dimensions can’t share one: SEM_qwen and LAME_qwen (Qwen3-VL, 4096-d) and SEM_clip (CLIP, 512-d, evaluation baseline only). The older Test_OLDSEM_qwen / Test_OLDSEM_dino collections are from earlier experiments.

The canonical numeric fields are indexed as `float` payload indexes, the categorical fields as `keyword`, and the identifier as `integer` (`SEMImageID`) or `keyword` (`image_id`) (`PAYLOAD_FIELDS_TO_INDEX` in each loader). This keeps metadata filtering fast.

## Indexing Workflow

From the repository root, with the environment set up (`source .venv/bin/activate`) and a valid vLLM token (see `docs/configuration.md`):

```bash
# LAME only: filter, crop and convert the raw images → data/LAME_filtered/   (notebook)
#   notebooks/lame_images.ipynb

# 1. Image embeddings (Qwen3-VL)
python src/sem_rag/scripts/generate_embeddings.py --dataset sem   # or --dataset lame

# 2. Build the collection (recreates it!) and upload documents, descriptions and thumbnails
python src/sem_rag/scripts/qdrant_upload.py --dataset sem    # → SEM_qwen
python src/sem_rag/scripts/qdrant_upload.py --dataset lame   # → LAME_qwen
```

Evaluation baselines (SEM only):

```bash
python src/sem_rag/scripts/generate_clip_embeddings.py
python src/sem_rag/scripts/qdrant_clip_upload.py          # → SEM_clip
python src/sem_rag/scripts/index_bm25.py                  # → data/bm25_index/
python src/sem_rag/scripts/generate_gabor_features.py     # → data/gabor_features/
```

## Development and Experimentation

Several notebooks in the repository were used during the development and evaluation of the indexing process.
Relevant notebooks include:

* `notebooks/lame_images.ipynb`: LAME filtering, cropping and a manifest of saved images
* `notebooks/embed.ipynb`: early Qwen/CLIP embedding experiments
* `notebooks/qdrant_upload.ipynb`: earlier notebook version of the upload (SEM and LAME)
* `notebooks/metadata_analysis.ipynb`: distribution of the canonical fields in `SEM_qwen` and `LAME_qwen`
* `notebooks/descriptions_analysis.ipynb`: statistics of the generated descriptions
* `notebooks/qdrant_analysis.ipynb`: analysis of the embedding spaces
* `notebooks/test_data.ipynb`: legacy test subset inspection

These notebooks were used to validate individual components and experiment with different representations before consolidating the indexing functionality in `src/sem_rag/scripts/qdrant_upload.py`.

## Result

After indexing, every indexed image has a searchable representation consisting of an image embedding and structured metadata:

```text
                SEM Sample
                    │
          ┌─────────┴─────────┐
          │                   │
        Image              Metadata
          │                   │
          ▼                   ▼
      Embedding        Structured payload
          │                   │
          ▼                   ▼
  Vector similarity    Metadata filtering
          │                   │
          └─────────┬─────────┘
                    │
                    ▼
                 Qdrant
```

This representation forms the static SEM knowledge base used by the retrieval pipeline.
