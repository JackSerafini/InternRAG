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
    GPTOSS_MODEL = "openai/gpt-oss-120b"
    EMBEDDING_MODEL = "Qwen/Qwen3-VL-Embedding-8B"


class TestSem:
    CROPS = DATA_DIR / "subset_test_1000/crops"
    JSON = DATA_DIR / "subset_test_1000/json"

    EMBEDDINGS_DINO = DATA_DIR / "subset_test_1000/embeddings"
    EMBEDDINGS_QWEN = DATA_DIR / "subset_test_1000/embeddings_QWEN"

    DESCRIPTIONS = DATA_DIR / "subset_test_1000/image_descriptions.json"

    THUMBNAIL_SIZE = (224, 224) # downsized preview for chat rendering, not a crop -> full field of view preserved, only resolution drops
    # tune down to (128,128) if payload size becomes an issue

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
    URL = "http://localhost:6333"

    COLLECTION_QWEN = "SEMImages_qwen"
    COLLECTION_DINO = "SEMImages_dino"
    COLLECTION_TEST = "Test"

    EMBEDDING_DIM_QWEN = 4096
    EMBEDDING_DIM_DINO = 768
