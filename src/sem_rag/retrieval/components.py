import json
import numpy as np

from haystack import component, Pipeline
from haystack.dataclasses import ChatMessage, Document
from haystack.components.builders import ChatPromptBuilder
from haystack.utils import Secret
from haystack_integrations.components.generators.vllm import VLLMChatGenerator

from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from sem_rag.config.settings import VLLM


INSTRUCTION = "Represent the user's input."

EXTRACTION_USER_PROMPT = """
Query:
{{ query }}

Metadata schema:
{{ metadata_schema }}

Extracted metadata:
"""


@component
class QueryMetadataExtractor:
    """
    Extract explicit metadata constraints from a natural-language query
    and convert valid constraints into Haystack/Qdrant filters.
    """
    def __init__(
        self,
        metadata_schema: dict,
        system_prompt: str,
        model: str = VLLM.GEMMA_MODEL,
        api_base_url: str = VLLM.API_URL,
        api_key: str | None = VLLM.API_KEY,
    ):
        """
        Args:
            metadata_schema: Dataset-specific schema (canonical fields, types,
                allowed values and filter tolerances).
            system_prompt: Dataset-specific extraction instructions.
            model: Generation model used for extraction.
            api_base_url: vLLM OpenAI-compatible endpoint.
            api_key: vLLM API key.
        """
        self.metadata_schema = metadata_schema
        self.metadata_schema_description = json.dumps(metadata_schema, indent=2, ensure_ascii=False)

        template = [
            ChatMessage.from_system(system_prompt),
            ChatMessage.from_user(EXTRACTION_USER_PROMPT),
        ]

        self.pipeline = Pipeline()

        self.pipeline.add_component(
            "builder",
            ChatPromptBuilder(
                template=template,
                required_variables={"query", "metadata_schema"},
            ),
        )
        self.pipeline.add_component(
            "llm",
            VLLMChatGenerator(
                model=model,
                api_key=Secret.from_token(api_key),
                api_base_url=api_base_url,
                generation_kwargs={"response_format": {"type": "json_object"}},
            )
        )
        self.pipeline.connect("builder", "llm")

    def build_condition(self, field: str, extracted: dict) -> dict | None:
        """Validate one extracted constraint and build its filter."""
        schema = self.metadata_schema[field]
        field_type = schema["type"]

        operator = extracted.get("operator")
        value = extracted.get("value")

        # __________ Categorical fields __________
        if field_type == "categorical":
            if operator != "==" or not isinstance(value, str):
                return None

            allowed_values = schema.get("values", {})

            if value not in allowed_values:
                return None

            return {
                "field": f"meta.{field}",
                "operator": "==",
                "value": value,
            }

        # __________ Numeric fields __________
        if field_type != "numeric":
            return None

        if operator not in {">=", "<=", "~", "between"}:
            return None

        # Numeric range
        if operator == "between":
            if not isinstance(value, list) or len(value) != 2:
                return None

            try:
                low = float(value[0])
                high = float(value[1])
            except (TypeError, ValueError):
                return None

            if low > high:
                low, high = high, low

            return {
                "operator": "AND",
                "conditions": [
                    {"field": f"meta.{field}", "operator": ">=", "value": low},
                    {"field": f"meta.{field}", "operator": "<=", "value": high},
                ],
            }

        # Single numeric value
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        # Approximate numeric value
        if operator == "~":
            filter_config = schema.get("filter", {})

            tolerance = filter_config.get("tolerance", 0.10)
            tolerance_type = filter_config.get("tolerance_type", "relative")

            delta = (abs(number) * tolerance if tolerance_type == "relative" else tolerance)

            return {
                "operator": "AND",
                "conditions": [
                    {"field": f"meta.{field}", "operator": ">=", "value": number - delta},
                    {"field": f"meta.{field}", "operator": "<=", "value": number + delta},
                ],
            }

        return {
            "field": f"meta.{field}",
            "operator": operator,
            "value": number,
        }

    @component.output_types(filters=dict[str, str])
    def run(self, query: str):
        """Extract metadata and return a combined filter, if applicable.

        Returns:
            filters: Combined Haystack filter, or None if no valid constraint was found.
            metadata: Raw JSON returned by the LLM, useful for evaluation.
        """
        result = self.pipeline.run({
            "builder": {"query": query, "metadata_schema": self.metadata_schema_description}
        })

        try:
            replies = result["llm"]["replies"]
            if not replies:
                return {"filters": None}

            metadata = json.loads(replies[0].text)

            if not isinstance(metadata, dict):
                return {"filters": None}

            conditions = []

            for field, extracted in metadata.items():
                if field not in self.metadata_schema:
                    continue

                if not isinstance(extracted, dict):
                    continue

                condition = self.build_condition(field, extracted)
                if condition is not None:
                    conditions.append(condition)

            if not conditions:
                return {"filters": None}

            return {"filters": {"operator": "AND", "conditions": conditions}}

        except Exception as exc:
            return {"filters": None}


@component
class QueryEmbedder:
    """
    Generate a Qwen3-VL embedding for a text query or uploaded image.

    When an image is present, the image is embedded directly. The query
    text is still passed separately to metadata extraction.
    """
    def __init__(
        self,
        model: str = VLLM.EMBEDDING_MODEL,
        api_base_url: str = VLLM.API_URL,
        api_key: str | None = VLLM.API_KEY
    ):
        self.model = model
        self.client = OpenAI(base_url=api_base_url, api_key=api_key)

    @component.output_types(embedding=list[float])
    def run(self, text: str = "", image_data_urls: list[str] | None = None):
        if image_data_urls:
            user_content = [
                {"type": "image_url", "image_url": {"url": image_data_urls[0]}},
                {"type": "text", "text": ""},
            ]
        else:
            user_content = [{"type": "text", "text": text}]

        messages = [
            {"role": "system", "content": [{"type": "text", "text": INSTRUCTION}]},
            {"role": "user", "content": user_content},
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


@component
class MMRReranker:
    """Select a diverse subset of candidates using Maximal Marginal Relevance."""
    def __init__(self, top_k: int = 5, lambda_: float = 0.8):
        """
        Args:
            top_k: Number of documents to keep.
            lambda_: Trade-off between relevance (1.0) and diversity (0.0).
        """
        self.top_k = top_k
        self.lambda_ = lambda_

    @component.output_types(documents=list[Document])
    def run(
        self,
        query_embedding: list[float],
        documents: list[Document],
    ):
        if not documents or self.top_k <= 0:
            return {"documents": []}

        if len(documents) <= self.top_k:
            return {"documents": documents}

        query = np.asarray(query_embedding, dtype=np.float32)
        embeddings = np.asarray([document.embedding for document in documents], dtype=np.float32)

        query = query / np.linalg.norm(query)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        query_similarities = embeddings @ query
        candidate_similarities = embeddings @ embeddings.T

        selected = [int(np.argmax(query_similarities))]
        remaining = set(range(len(documents))) - set(selected)

        while len(selected) < self.top_k and remaining:
            mmr_scores = []

            for candidate in remaining:
                relevance = query_similarities[candidate]
                redundancy = np.max(candidate_similarities[candidate, selected])

                mmr = self.lambda_ * relevance - (1 - self.lambda_) * redundancy
                mmr_scores.append((mmr, candidate))

            _, best_candidate = max(mmr_scores)

            selected.append(best_candidate)
            remaining.remove(best_candidate)

        return {"documents": [documents[i] for i in selected]}
