"""
Hayhooks PipelineWrapper for the QWEN RAG retrieval pipeline.
"""
import os
import json
from collections.abc import Generator
from typing import Union, Dict, List

from haystack import Pipeline, component
from haystack.utils import Secret
from haystack.components.builders import AnswerBuilder, ChatPromptBuilder
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.generators.vllm import VLLMChatGenerator
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

from hayhooks import BasePipelineWrapper, log, streaming_generator

from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

# __________ BASE CONFIGURATION __________ #
VLLM_API_KEY = os.getenv("VLLM_API_KEY")
API_URL = os.getenv("VLLM_API_URL", "https://orfeo-llm.areasciencepark.it/vllm/v1")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.orfeo-rag.svc.cluster.local:6333")

THUMBNAIL_BASE_URL = os.getenv("THUMBNAIL_BASE_URL", "https://llm-rag.dev.rd.areasciencepark.it/rag-images")
# THUMBNAIL_BASE_URL = os.getenv("THUMBNAIL_BASE_URL", "https://chat.local/rag-images")

# __________ MANUAL CONFIGURATION __________ #
GENERATION_MODEL_ID = "google/gemma-4-26B-A4B-it"
EMBED_MODEL_ID = "Qwen/Qwen3-VL-Embedding-8B"
EMBEDDING_DIM = 4096

QDRANT_COLLECTION = "Test_OLDSEM_qwen"

TEMPLATE = [
    ChatMessage.from_system(
        """
        You are an expert in Scanning Electron Microscopy (SEM), helping a
        researcher review SEM image candidates that have already been
        ranked by visual similarity to their query. The ranking was done
        by the retrieval system, not by you -- do not assign relevance
        scores or claim to judge how well an image matches the query.

        The actual images will be shown to the researcher separately.
        Your job is to briefly summarize what distinguishes each
        candidate: visible morphology described in the notes below,
        magnification, working distance, beam time, and any other
        relevant microscope settings that might help the researcher pick
        one to inspect further.

        Do NOT invent information. Use only the retrieved context.
        """
    ),
    ChatMessage.from_user(
        """
        User query:

        {{ question }}

        Retrieved candidates:

        {% for document in documents %}

        ----------------------------------------

        {{ document.content }}

        ----------------------------------------

        {% endfor %}
        """
    )
]

INSTRUCTION = "Represent the user's input."

METADATA_FIELDS = [
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

# Right now, all fields are taken relative to the value passed, ±10%
# TODO: tune this -> some might need an absolute range (e.g., ±10% of a very small value will practically be exact)
FIELD_CONFIG = {
    "AP_WD":             {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_FREE_WD":        {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"}, 
    "AP_BEAM_TIME":      {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_STAGE_LOW_Z":    {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_STAGE_CENTRE_X": {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_C3":             {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_EHT_CAL_30KV":   {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_EHT_CAL_10KV":   {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_EHT_CAL_100":    {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_EHT_CAL_24KV":   {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
    "AP_MINMAG":         {"type": "range", "tolerance": 0.10, "tolerance_type": "relative"},
}

VALID_OPERATORS = {">=", "<=", "~", "between"}

if not VLLM_API_KEY:
    raise RuntimeError("VLLM_API_KEY is not set.")

def get_document_store() -> QdrantDocumentStore:
    """
    Returns a QdrantDocumentStore pointing at the shared, persistent, in-cluster Qdrant instance.
    """
    return QdrantDocumentStore(
        url=QDRANT_URL,
        index=QDRANT_COLLECTION,
        embedding_dim=EMBEDDING_DIM,
    )

def get_vllm_secret() -> Secret:
    return Secret.from_token(VLLM_API_KEY)


@component
class QueryMetadataExtractor():
    def __init__(self):
        template = [
            ChatMessage.from_system(
                """
                You are part of an information system that processes users queries.
                Given a user query you extract information from it that matches a given list of metadata fields.
                The information to be extracted from the query must match the semantics associated with the given metadata fields.
                The information that you extracted from the query will then be used as filters to narrow down the search space
                when querying an index.

                For each field you extract, return an object with "operator" and "value":
                - ">="      -> greater than or equal to value
                - "<="      -> less than or equal to value
                - "~"       -> approximately equal to value (use this when the user says "around", "about", "roughly",
                            "approximately", or gives an exact-sounding value with no qualifier, e.g. "=", "exactly")
                - "between" -> use this when the user gives a range with two bounds; "value" must then be a list of
                            two numbers [low, high] instead of a single number

                The extracted information in 'Extracted metadata' must be returned as a valid JSON structure.
                Only include a key in the output if the query explicitly provides or clearly implies its value.
                If no metadata fields are present in the query, return an empty JSON object: {}
                ###
                Example 1:
                Query: "What is the resolution of this microscope image?"
                Metadata fields: ["AP_WD", "AP_BEAM_TIME"]
                Extracted metadata fields: {}
                ###
                Example 2:
                Query: "Show me images with a working distance around 8mm"
                Metadata fields: ["AP_WD", "AP_BEAM_TIME"]
                Extracted metadata fields: {"AP_WD": {"operator": "~", "value": 8}}
                ###
                Example 3:
                Query: "Find images with beam time greater than 30 seconds"
                Metadata fields: ["AP_WD", "AP_BEAM_TIME"]
                Extracted metadata fields: {"AP_BEAM_TIME": {"operator": ">=", "value": 30}}
                ###
                Example 4:
                Query: "Show me images with working distance below 5mm"
                Metadata fields: ["AP_WD", "AP_BEAM_TIME"]
                Extracted metadata fields: {"AP_WD": {"operator": "<=", "value": 5}}
                ###
                Example 5:
                Query: "Show me images with beam time between 20 and 40 seconds"
                Metadata fields: ["AP_WD", "AP_BEAM_TIME"]
                Extracted metadata fields: {"AP_BEAM_TIME": {"operator": "between", "value": [20, 40]}}
                """
            ),
            ChatMessage.from_user(
                """
                Query: {{ query }}
                Metadata fields: {{ metadata_fields }}
                Extracted metadata fields:
                """
            ),
        ]

        self.pipeline = Pipeline()
        self.pipeline.add_component("builder", ChatPromptBuilder(template=template, required_variables={"query", "metadata_fields"}))
        self.pipeline.add_component("llm", VLLMChatGenerator(model=GENERATION_MODEL_ID, api_key=get_vllm_secret(), api_base_url=API_URL, generation_kwargs={"response_format": {"type": "json_object"}}))
        self.pipeline.connect("builder", "llm")

    def build_condition(self, field: str, extracted: dict, config: dict):
        operator = extracted.get("operator")
        value = extracted.get("value")

        if operator not in VALID_OPERATORS:
            return None  # guard against hallucinated operator strings

        if operator == "between":
            if not (isinstance(value, list) and len(value) == 2):
                return None  # malformed range, drop rather than guess
            try:
                low, high = float(value[0]), float(value[1])
            except (TypeError, ValueError):
                return None
            if low > high:
                low, high = high, low  # tolerate reversed bounds from the LLM
            return {
                "operator": "AND",
                "conditions": [
                    {"field": f"meta.{field}", "operator": ">=", "value": low},
                    {"field": f"meta.{field}", "operator": "<=", "value": high},
                ],
            }
        
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None  # LLM gave something non-numeric for a numeric field, drop it

        if operator == "~":
            tol = config.get("tolerance", 0.1)
            # If it not "relative", it will be absolute -> take as delta the absolute tolerance set
            delta = abs(value) * tol if config.get("tolerance_type", "relative") == "relative" else tol
            return {
                "operator": "AND",
                "conditions": [
                    {"field": f"meta.{field}", "operator": ">=", "value": value - delta},
                    {"field": f"meta.{field}", "operator": "<=", "value": value + delta},
                ],
            }

        # ">=", "<=" map directly onto Qdrant's own operator strings
        return {"field": f"meta.{field}", "operator": operator, "value": value}

    @component.output_types(filters=Dict[str, str])
    def run(self, query: str, metadata_fields: List[str]):
        result = self.pipeline.run({'builder': {'query': query, 'metadata_fields': metadata_fields}})
        try:
            metadata = json.loads(result['llm']['replies'][0].text) # key/value pairs the LLM decided to extract

            conditions = []
            for key, extracted in metadata.items():
                if key not in metadata_fields:
                    continue  # guard against hallucinated field names
                config = FIELD_CONFIG.get(key, {"type": "range"})
                cond = self.build_condition(key, extracted, config)
                if cond is not None:
                    conditions.append(cond)

            if not conditions:
                return {"filters": None}

            return {"filters": {"operator": "AND", "conditions": conditions}}
        except Exception:
            return {"filters": None}


@component
class QueryEmbedder():
    def __init__(self, model: str, api_base_url: str, api_key: str):
        self.model = model
        self.client = OpenAI(base_url=api_base_url, api_key=api_key)

    @component.output_types(embedding=list[float])
    def run(self, text: str = "", image_data_urls: list[str] | None = None):
        if image_data_urls:
            messages = [
                {"role": "system", "content": [{"type": "text", "text": INSTRUCTION,}]},
                {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image_data_urls[0]}},
                        {"type": "text", "text": ""},
                ]},
                {"role": "assistant", "content": [{"type": "text", "text": ""}]},
            ]
        else:
            messages = [
                {"role": "system", "content": [{"type": "text", "text": INSTRUCTION,}]},
                {"role": "user", "content": [{"type": "text", "text": text}]},
                {"role": "assistant", "content": [{"type": "text", "text": ""}]},
            ]

        response: CreateEmbeddingResponse = self.client.post(
            "/embeddings",
            cast_to=CreateEmbeddingResponse,
            body={
                "messages": messages,
                "model": self.model,
                "encoding_format": "float",
                "continue_final_message": True,
                "add_special_tokens": True,
            },
        )

        return {"embedding": response.data[0].embedding}


def render_image_gallery(documents) -> str:
    """
    Render the retrieved candidates as inline images so the researcher can
    actually see what's being discussed, not just read a paraphrase of it.
    """
    if not documents:
        return ""

    gallery = "\n\n**Candidate images:**\n"
    for idx, doc in enumerate(documents, start=1):
        label = doc.meta.get("ImageOriginalName", doc.id)
        gallery += f"\n{idx}. {label}\n"
        gallery += f"\n![{label}]({THUMBNAIL_BASE_URL}/{doc.id}.png)\n"
    return gallery

def on_pipeline_end(result: dict) -> str:
    """
    Called once after the streamed LLM output finishes.

    `result` is the full pipeline.run() output dict, keyed by component name
    (same shape as the non-streaming path). We pull the documents the
    retriever found and append them as a source list, since the streaming
    path skips AnswerBuilder and would otherwise surface no citations at all.

    Whatever this returns is appended to the message Open WebUI displays.
    """
    answers = result.get("answer_builder", {}).get("answers", [])
    if not answers:
        return ""
    documents = answers[0].documents
    return render_image_gallery(documents)


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        document_store = get_document_store()

        pipeline = Pipeline()
        pipeline.add_component("query_embedder", QueryEmbedder(model=EMBED_MODEL_ID, api_base_url=API_URL, api_key=VLLM_API_KEY))
        pipeline.add_component("retriever", QdrantEmbeddingRetriever(document_store=document_store, top_k=5))
        pipeline.connect("query_embedder.embedding", "retriever")

        pipeline.add_component("metadata_extractor", QueryMetadataExtractor()) # TODO
        pipeline.connect("metadata_extractor.filters", "retriever.filters") # TODO

        pipeline.add_component("prompt_builder", ChatPromptBuilder(template=TEMPLATE, required_variables={"question", "documents"}))
        pipeline.connect("retriever", "prompt_builder")

        pipeline.add_component("llm", VLLMChatGenerator(model=GENERATION_MODEL_ID, api_key=get_vllm_secret(), api_base_url=API_URL))
        pipeline.connect("prompt_builder", "llm")

        pipeline.add_component("answer_builder", AnswerBuilder())
        pipeline.connect("llm", "answer_builder")
        pipeline.connect("retriever", "answer_builder")

        self.pipeline = pipeline

    def extract_query(self, messages: list[dict]):
        msg = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        if msg is None:
            return "", []

        content = msg.get("content", "")
        if isinstance(content, str):
            return content, []

        text, images = "", []

        for part in content:
            if part.get("type") == "text":
                text += part.get("text", "")

            elif part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url")
                if url:
                    images.append(url)

        return text, images

    def run_chat_completion(self, model: str, messages: list[dict], body: dict) -> Union[str, Generator]:
        question, images = self.extract_query(messages)
        log.trace("Question: {}", question)

        if body.get("stream", False):
            # Real token-by-token streaming: streaming_generator wires up
            # llm's streaming_callback under the hood and yields chunks as
            # the VLLMChatGenerator produces them.
            return streaming_generator(
                pipeline=self.pipeline,
                pipeline_run_args={
                    "metadata_extractor": {"query": question, "metadata_fields": METADATA_FIELDS}, # NOTE
                    "query_embedder": {"text": question, "image_data_urls": images},
                    "prompt_builder": {"question": question},
                    "answer_builder": {"query": question},
                },
                on_pipeline_end=on_pipeline_end,
            )

        # Non-streaming path: run synchronously and return the final text.
        response = self.pipeline.run(
            {
                "metadata_extractor": {"query": question, "metadata_fields": METADATA_FIELDS}, # NOTE
                "query_embedder": {"text": question, "image_data_urls": images},
                "prompt_builder": {"question": question},
                "answer_builder": {"query": question},
            }
        )
        answers = response.get("answer_builder", {}).get("answers", [])
        if not answers:
            return "Sorry, I couldn't generate an answer."
        
        return answers[0].data + render_image_gallery(answers[0].documents)