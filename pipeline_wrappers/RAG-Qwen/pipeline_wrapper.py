"""
Hayhooks PipelineWrapper for the QWEN RAG retrieval pipeline.
"""
import os
from collections.abc import Generator
from typing import Union

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

THUMBNAIL_BASE_URL = os.getenv("THUMBNAIL_BASE_URL", "https://chat.local/rag-images")

# __________ MANUAL CONFIGURATION __________ #
GENERATION_MODEL_ID = "google/gemma-4-26B-A4B-it"
EMBED_MODEL_ID = "Qwen/Qwen3-VL-Embedding-8B"
EMBEDDING_DIM = 4096

QDRANT_COLLECTION = "SEMImages_qwen"

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

''' NOTE: this is just a try to implement a metadata extractor from a query
@component()
class QueryMetadataExtractor:
    def __init__(self):
        template = [
            ChatMessage.from_user(
            """
            You are part of an information system that processes users queries.
            Given a user query you extract information from it that matches a given list of metadata fields.
            The information to be extracted from the query must match the semantics associated with the given metadata fields.
            The information that you extracted from the query will then be used as filters to narrow down the search space
            when querying an index.
            Just include the value of the extracted metadata without including the name of the metadata field.
            The extracted information in 'Extracted metadata' must be returned as a valid JSON structure.
            Only include a key in the output if the query explicitly provides or clearly implies its value.
            If no metadata fields are present in the query, return an empty JSON object: {}
            ###
            Example 1:
            Query: "What was the revenue of Nvidia in 2022?"
            Metadata fields: {"company", "year"}
            Extracted metadata fields: {"company": "nvidia", "year": 2022}
            ###
            Example 2:
            Query: "What were the most influential publications in 2023 regarding Alzheimer's disease?"
            Metadata fields: {"disease", "year"}
            Extracted metadata fields: {"disease": "Alzheimer", "year": 2023}
            ###
            Example 3:
            Query: "What is the resolution of this microscope image?"
            Metadata fields: {"AP_WD", "AP_BEAM_TIME"}
            Extracted metadata fields: {}
            """
            )
        ]

        prompt_builder = ChatPromptBuilder(template=template)
        llm = VLLMChatGenerator(
            model=GENERATION_MODEL_ID,
            api_key=get_vllm_secret(),
            api_base_url=API_URL,
            generation_kwargs={"response_format": {"type": "json_object"}},
        )

        self.pipeline = Pipeline()
        self.pipeline.add_component(name="builder", instance=prompt_builder)
        self.pipeline.add_component(name="llm", instance=llm)
        self.pipeline.connect("builder", "llm")

    @component.output_types(filters=Dict[str, Any])
    def run(self, query: str, metadata_fields: List[str]):
        result = self.pipeline.run({'builder': {'query': query, 'metadata_fields': metadata_fields}})
        try:
            metadata = json.loads(result['llm']['replies'][0].text)

            # this can be done with specific data structures and in a more sophisticated way
            filters = [
                {"field": f"meta.{key}", "operator": "==", "value": value}
                for key, value in metadata.items()
                if key in metadata_fields  # guard against hallucinated field names
            ]

            if not filters:
                return {"filters": None}  # explicit: no filtering

            return {"filters": {"operator": "AND", "conditions": filters}}
        except:
            return {"filters": None}
'''


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

        # pipeline.add_component("metadata_extractor", QueryMetadataExtractor()) # NOTE: this is just a try
        # pipeline.connect("metadata_extractor.filters", "retriever.filters") # NOTE: this is just a try

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
        # metadata_fields = [
        #     "AP_WD",
        #     "AP_FREE_WD",
        #     "AP_BEAM_TIME",
        #     "AP_STAGE_LOW_Z",
        #     "AP_STAGE_CENTRE_X",
        #     "AP_C3",
        #     "AP_EHT_CAL_30KV",
        #     "AP_EHT_CAL_10KV",
        #     "AP_EHT_CAL_100",
        #     "AP_EHT_CAL_24KV",
        #     "AP_MINMAG",
        # ]

        if body.get("stream", False):
            # Real token-by-token streaming: streaming_generator wires up
            # llm's streaming_callback under the hood and yields chunks as
            # the VLLMChatGenerator produces them.
            return streaming_generator(
                pipeline=self.pipeline,
                pipeline_run_args={
                    # "metadata_extractor": {"query": question, "metadata_fields": metadata_fields}, # NOTE
                    "query_embedder": {"text": question, "image_data_urls": images},
                    "prompt_builder": {"question": question},
                    "answer_builder": {"query": question},
                },
                on_pipeline_end=on_pipeline_end,
            )

        # Non-streaming path: run synchronously and return the final text.
        response = self.pipeline.run(
            {
                # "metadata_extractor": {"query": question, "metadata_fields": metadata_fields}, # NOTE
                "query_embedder": {"text": question, "image_data_urls": images},
                "prompt_builder": {"question": question},
                "answer_builder": {"query": question},
            }
        )
        answers = response.get("answer_builder", {}).get("answers", [])
        if not answers:
            return "Sorry, I couldn't generate an answer."
        
        return answers[0].data + render_image_gallery(answers[0].documents)