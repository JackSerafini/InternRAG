"""
Hayhooks PipelineWrapper for the RAG retrieval pipeline.
"""
from collections.abc import Generator
from typing import Union

from haystack import Pipeline
from haystack.components.builders import AnswerBuilder, ChatPromptBuilder
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.embedders.vllm import VLLMTextEmbedder
from haystack_integrations.components.generators.vllm import VLLMChatGenerator
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

from hayhooks import BasePipelineWrapper, get_last_user_message, log, streaming_generator

from app.common import (
    API_URL,
    EMBED_MODEL_ID,
    GENERATION_MODEL_ID,
    get_document_store,
    get_vllm_secret,
)

def on_pipeline_end(result: dict) -> str:
    """
    Called once after the streamed LLM output finishes.

    `result` is the full pipeline.run() output dict, keyed by component name
    (same shape as the non-streaming path). We pull the documents the
    retriever found and append them as a source list, since the streaming
    path skips AnswerBuilder and would otherwise surface no citations at all.

    Whatever this returns is appended to the message Open WebUI displays.
    """
    documents = result.get("retriever", {}).get("documents", [])
    if not documents:
        return ""

    sources_str = "\n\n**Sources:**\n"
    for idx, doc in enumerate(documents, start=1):
        # Adjust the metadata key to whatever you actually store per-document
        # (e.g. doc.meta["file_name"], doc.meta["url"], doc.meta["source"]).
        label = doc.meta.get("source") or doc.meta.get("file_name") or doc.id
        sources_str += f"{idx}. {label}\n"
    return sources_str

TEMPLATE = [
    ChatMessage.from_user(
        """
        You have to answer the following question based on the given context information only.
        Context:
        {% for document in documents %}
            {{ document.content }}
        {% endfor %}
        Question: {{question}}
        Answer:
        """
    )
]

class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        document_store = get_document_store()

        query_embedder = VLLMTextEmbedder(
            model=EMBED_MODEL_ID,
            api_key=get_vllm_secret(),
            api_base_url=API_URL,
        )
        retriever = QdrantEmbeddingRetriever(document_store=document_store, top_k=3)
        prompt_builder = ChatPromptBuilder(
            template=TEMPLATE, required_variables={"question", "documents"}
        )
        llm = VLLMChatGenerator(
            model=GENERATION_MODEL_ID,
            api_key=get_vllm_secret(),
            api_base_url=API_URL,
        )
        answer_builder = AnswerBuilder()

        pipeline = Pipeline()
        pipeline.add_component("query_embedder", query_embedder)
        pipeline.add_component("retriever", retriever)
        pipeline.connect("query_embedder.embedding", "retriever")

        pipeline.add_component("prompt_builder", prompt_builder)
        pipeline.connect("retriever", "prompt_builder")

        pipeline.add_component("llm", llm)
        pipeline.connect("prompt_builder", "llm")

        pipeline.add_component("answer_builder", answer_builder)
        pipeline.connect("llm", "answer_builder")
        pipeline.connect("retriever", "answer_builder")

        self.pipeline = pipeline

    def run_chat_completion(self, model: str, messages: list[dict], body: dict) -> Union[str, Generator]:
        question = get_last_user_message(messages)
        log.trace("Question: {}", question)

        if body.get("stream", False):
            # Real token-by-token streaming: streaming_generator wires up
            # llm's streaming_callback under the hood and yields chunks as
            # the VLLMChatGenerator produces them.
            return streaming_generator(
                pipeline=self.pipeline,
                pipeline_run_args={
                    "query_embedder": {"text": question},
                    "prompt_builder": {"question": question},
                    "answer_builder": {"query": question},
                },
                on_pipeline_end=on_pipeline_end,
            )

        # Non-streaming path: run synchronously and return the final text.
        response = self.pipeline.run(
            {
                "query_embedder": {"text": question},
                "prompt_builder": {"question": question},
                "answer_builder": {"query": question},
            }
        )
        answers = response.get("answer_builder", {}).get("answers", [])
        if not answers:
            return "Sorry, I couldn't generate an answer."
        return answers[0].data