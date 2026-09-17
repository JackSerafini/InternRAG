import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"

NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"

HF_TOKEN = os.getenv("HF_TOKEN")

class VLLM:
    API_KEY = os.getenv("VLLM_API_KEY")
    API_URL = os.getenv("VLLM_API_URL", "https://orfeo-llm.areasciencepark.it/vllm/v1")

    GEMMA_MODEL = "google/gemma-4-26B-A4B-it"
    QWEN36_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"
    QWEN38_MODEL = "Qwen/Qwen3.8-27B-FP8"
    EMBEDDING_MODEL = "Qwen/Qwen3-VL-Embedding-8B"


class SEMDataset:
    SEM_DIR = DATA_DIR / "SEM"

    CROPS = SEM_DIR / "crops"
    JSON = SEM_DIR / "json"

    EMBEDDINGS_QWEN = SEM_DIR / "embeddings_QWEN"
    EMBEDDINGS_CLIP = SEM_DIR / "embeddings_CLIP"
    EMBEDDINGS_DINO = SEM_DIR / "embeddings_DINOv3"

    CATEGORICAL_SETTINGS = SEM_DIR / "SEM_RAG_categorical_fields_dictionary.csv"
    NUMERICAL_SETTINGS = SEM_DIR / "SEM_RAG_numeric_fields_dictionary.csv"
    CATEGORIES = SEM_DIR / "filtered_categories.csv"
    
    DESCRIPTIONS = SEM_DIR / "image_descriptions.json"

    THUMBNAIL_SIZE = (224, 224) # downsized preview for chat rendering, not a crop (tune down to (128,128) if payload size becomes an issue)


class TestSem:
    CROPS = DATA_DIR / "subset_test_1000/crops"
    JSON = DATA_DIR / "subset_test_1000/json"

    EMBEDDINGS_DINO = DATA_DIR / "subset_test_1000/embeddings"
    EMBEDDINGS_QWEN = DATA_DIR / "subset_test_1000/embeddings_QWEN"

    DESCRIPTIONS = DATA_DIR / "subset_test_1000/image_descriptions.json"

    THUMBNAIL_SIZE = (224, 224)

    SETTINGS_KEYS = [
        "AP_WD",
        "AP_FREE_WD",
        "AP_BEAM_TIME",
        "AP_STAGE_LOW_Z",
        "AP_STAGE_CENTRE_X",
        "AP_C3",
        "AP_EHT_CAL_30KV",
        "AP_EHT_CAL_10KV",
        "AP_EHT_CAL_100",
        "AP_EHT_CAL_24KV",
        "AP_MINMAG",
    ]


class Qdrant:
    URL = "http://db-rag.dev.rd.areasciencepark.it"

    COLLECTION_QWEN = "SEM_qwen"
    OLD_COLLECTION_QWEN = "Test_OLDSEM_qwen"
    OLD_COLLECTION_DINO = "Test_OLDSEM_dino"
    COLLECTION_CLIP = "SEM_clip"
    COLLECTION_TEST = "Test"

    EMBEDDING_DIM_QWEN = 4096
    EMBEDDING_DIM_DINO = 768
    EMBEDDING_DIM_CLIP = 512

class Evaluation:
    BM25_DIR = DATA_DIR / "bm25_index"

    GABOR_FILE = DATA_DIR / "gabor_features/gabor_features.npz"
