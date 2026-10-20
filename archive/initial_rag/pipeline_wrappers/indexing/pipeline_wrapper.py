"""
Hayhooks PipelineWrapper for the indexing pipeline.
"""
import os
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import UploadFile
from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack.utils import Secret
from haystack_integrations.components.converters.docling import DoclingConverter, ExportType
from haystack_integrations.components.embedders.vllm import VLLMDocumentEmbedder
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from hayhooks import BasePipelineWrapper, log

logger = logging.getLogger("indexing-pipeline")

# __________ BASE CONFIGURATION __________ #
VLLM_API_KEY = os.getenv("VLLM_API_KEY")
API_URL = os.getenv("VLLM_API_URL", "https://orfeo-llm.areasciencepark.it/vllm/v1")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.orfeo-rag.svc.cluster.local:6333")

# __________ MANUAL CONFIGURATION __________ #
EMBED_MODEL_ID = "Qwen/Qwen3-VL-Embedding-8B"
EMBEDDING_DIM = 4096 # NOTE
QDRANT_COLLECTION = "Test"

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".md", ".txt"} # -> adjust
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB -> adjust

if not VLLM_API_KEY:
    raise RuntimeError("VLLM_API_KEY is not set.")

def get_document_store() -> QdrantDocumentStore:
    return QdrantDocumentStore(
        url=QDRANT_URL,
        index=QDRANT_COLLECTION,
        embedding_dim=EMBEDDING_DIM,
    )

def get_vllm_secret() -> Secret:
    return Secret.from_token(VLLM_API_KEY)


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        document_store = get_document_store()

        converter = DoclingConverter(export_type=ExportType.DOC_CHUNKS)
        embedder = VLLMDocumentEmbedder(
            model=EMBED_MODEL_ID,
            api_key=get_vllm_secret(),
            api_base_url=API_URL,
        )
        writer = DocumentWriter(document_store=document_store)

        pipeline = Pipeline()
        pipeline.add_component("converter", converter)
        pipeline.add_component("embedder", embedder)
        pipeline.connect("converter", "embedder")

        pipeline.add_component("writer", writer)
        pipeline.connect("embedder", "writer")

        self.pipeline = pipeline

    def run_api(self, files: List[UploadFile]) -> dict:
        """
        Hayhooks detects the `files: List[UploadFile]` parameter and
        automatically exposes this as a multipart/form-data endpoint
        (POST /<pipeline_name>/run), instead of a JSON body.
        """
        results = []
        for file in files:
            suffix = Path(file.filename).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
                })
                continue

            contents = file.file.read()
            if len(contents) > MAX_FILE_SIZE_BYTES:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": "File too large.",
                })
                continue

            tmp_dir = Path(tempfile.mkdtemp(prefix="upload_"))
            tmp_path = tmp_dir / file.filename
            try:
                with open(tmp_path, "wb") as f:
                    f.write(contents)

                log.trace("Indexing file: {} ({} bytes)", file.filename, len(contents))
                result = self.pipeline.run({"converter": {"sources": [str(tmp_path)]}})
                n_written = result.get("writer", {}).get("documents_written")

                results.append({
                    "filename": file.filename,
                    "status": "indexed",
                    "documents_written": n_written,
                })
            except Exception as e:
                logger.exception("Failed to index %s", file.filename)
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "detail": str(e),
                })
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        return {"results": results}