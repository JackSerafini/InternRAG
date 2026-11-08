import os
import json
import numpy as np
from collections.abc import Generator
from typing import Union

from haystack import Pipeline, component
from haystack.utils import Secret
from haystack.components.builders import AnswerBuilder, ChatPromptBuilder
from haystack.dataclasses import Document, ChatMessage
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

# __________ MANUAL CONFIGURATION __________ #
THUMBNAIL_BASE_URL = "https://llm-rag.dev.rd.areasciencepark.it/rag-images-lame"

GENERATION_MODEL_ID = "google/gemma-4-26B-A4B-it"
EMBED_MODEL_ID = "Qwen/Qwen3-VL-Embedding-8B"
EMBEDDING_DIM = 4096

MMR_CANDIDATES = 50
TOP_K = 5
MMR_LAMBDA = 0.8

QDRANT_COLLECTION = "LAME_qwen"

INSTRUCTION = "Represent the user's input."


if not VLLM_API_KEY:
    raise RuntimeError("VLLM_API_KEY is not set.")


# __________ METADATA SCHEMA __________ #
METADATA_SCHEMA = {
    # __________ Numeric fields __________
    "magnification_x": {
        "type": "numeric",
        "description": (
            "Nominal SEM magnification used when the image was acquired. "
            "It describes the enlargement factor applied to the specimen image."
        ),
        "dictionary_terms": [
            "magnification",
            "mag",
            "magnified",
            "magnification factor",
            "times magnification",
            "x magnification",
            "kx",
            "KX",
            "zoom level",
        ],
        "unit": "X",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "accelerating_voltage_kv": {
        "type": "numeric",
        "description": (
            "Electron beam accelerating voltage used during SEM image "
            "acquisition. It influences electron penetration, interaction "
            "volume, surface sensitivity, charging behaviour and signal generation."
        ),
        "dictionary_terms": [
            "accelerating voltage",
            "acceleration voltage",
            "accelerator voltage",
            "beam voltage",
            "electron beam voltage",
            "EHT",
            "high voltage",
            "HV",
            "voltage",
            "kV",
            "kilovolt",
            "kilovolts",
        ],
        "unit": "kV",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "emission_current_µa": {
        "type": "numeric",
        "description": (
            "Electron emission current recorded in the SEM acquisition "
            "metadata. It characterizes the electron source operating "
            "conditions during image acquisition."
        ),
        "dictionary_terms": [
            "emission current",
            "electron emission current",
            "source current",
            "beam current",
            "emission current in microamps",
            "emission current in microamperes",
            "µA",
            "uA",
            "microamp",
            "microamps",
            "microampere",
            "microamperes",
        ],
        "unit": "µA",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "dwell_time_µs": {
        "type": "numeric",
        "description": (
            "Electron beam dwell time per pixel during SEM image acquisition. "
            "It influences the signal collected at each pixel and the "
            "trade-off between acquisition time, signal-to-noise ratio and "
            "potential beam-induced effects."
        ),
        "dictionary_terms": [
            "dwell time",
            "pixel dwell time",
            "beam dwell time",
            "pixel time",
            "scan dwell time",
            "dwell duration",
            "µs",
            "us",
            "microsecond",
            "microseconds",
        ],
        "unit": "µs",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "working_distance_mm": {
        "type": "numeric",
        "description": (
            "Working distance between the specimen and the relevant SEM "
            "column or pole-piece reference during image acquisition. "
            "It influences imaging geometry, depth of field and detector "
            "conditions."
        ),
        "dictionary_terms": [
            "working distance",
            "WD",
            "working distance mm",
            "specimen working distance",
            "sample working distance",
            "distance to sample",
            "distance to specimen",
            "mm",
            "millimeter",
            "millimeters",
            "millimetre",
            "millimetres",
        ],
        "unit": "mm",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    # __________ Categorical fields __________
    "scan_mode": {
        "type": "categorical",
        "description": (
            "SEM scan mode recorded in the acquisition metadata. "
            "It identifies the acquisition mode used to produce the image."
        ),
        "values": {
            "ANALYSIS": {
                "description": (
                    "Acquisition mode identified by the instrument metadata "
                    "as ANALYSIS."
                ),
                "dictionary_terms": [
                    "ANALYSIS",
                    "analysis mode",
                    "analytical mode",
                    "analysis acquisition",
                ],
            },
            "UH-RESOLUTION": {
                "description": (
                    "High-resolution acquisition mode identified by the "
                    "instrument metadata as UH-RESOLUTION."
                ),
                "dictionary_terms": [
                    "UH-RESOLUTION",
                    "UH RESOLUTION",
                    "ultra-high resolution",
                    "ultra high resolution",
                    "high-resolution mode",
                    "high resolution mode",
                ],
            },
            "WIDE FIELD": {
                "description": (
                    "Acquisition mode identified by the instrument metadata "
                    "as WIDE FIELD."
                ),
                "dictionary_terms": [
                    "WIDE FIELD",
                    "WIDE-FIELD",
                    "widefield",
                    "wide field mode",
                    "wide-field mode",
                ],
            },
        },
    },

    "detector": {
        "type": "categorical",
        "description": (
            "Detector configuration recorded in the SEM acquisition metadata. "
            "The complete stored value is preserved for exact metadata filtering."
        ),
        "values": {
            "Axial": {
                "description": "Axial detector configuration.",
                "dictionary_terms": [
                    "Axial",
                    "Axial detector",
                ],
            },
            "Axial (BSE)": {
                "description": "Axial detector configuration labelled BSE.",
                "dictionary_terms": [
                    "Axial (BSE)",
                    "Axial BSE",
                    "Axial backscattered electron detector",
                ],
            },
            "E-T": {
                "description": "E-T detector configuration.",
                "dictionary_terms": [
                    "E-T",
                    "E T",
                    "ET detector",
                    "Everhart-Thornley detector",
                    "Everhart Thornley detector",
                ],
            },
            "LE BSE": {
                "description": "Low-energy backscattered-electron detector configuration.",
                "dictionary_terms": [
                    "LE BSE",
                    "LE-BSE",
                    "LEBSE",
                    "low-energy backscattered electrons",
                    "low energy backscattered electrons",
                ],
            },
            "MD": {
                "description": "MD detector configuration.",
                "dictionary_terms": [
                    "MD",
                    "MD detector",
                ],
            },
            "STEM": {
                "description": "Scanning transmission electron detector "
                "(transmitted-electron signal: bright field, dark field or "
                "high-angle annular dark field).",
                "dictionary_terms": [
                    "STEM",
                    "STEM detector",
                    "transmitted electrons",
                    "TE",
                    "TE BF",
                    "TE DF",
                    "TE HADF",
                    "bright field",
                    "dark field",
                    "HAADF"
                ],
            },
        },
    },
}

METADATA_SCHEMA_DESCRIPTION = json.dumps(METADATA_SCHEMA, indent=2, ensure_ascii=False)


TEMPLATE = [
    ChatMessage.from_system(
        """
        You are an expert in Scanning Electron Microscopy (SEM), helping a
        researcher review retrieved SEM images.

        The retrieval system has already selected the candidate images.
        Do not assign relevance scores, rank candidates, or claim to judge
        how well an image matches the query.

        The actual images will be shown to the researcher separately.

        For each candidate, produce a concise summary using only the
        information available in the retrieved context.

        OUTPUT FORMAT:

        **Image <ID>**

        **Morphology:** <brief description>

        **Metadata:** <field name>: <value> | <field name>: <value> | ...

        FORMATTING RULES:
        
        - Always write the image identifier in bold as **Image <ID>**.
        - Always write **Morphology:** and **Metadata:** in bold.
        - Do not use bullet points for Morphology or Metadata.
        - Put the complete metadata on a single line.
        - For every metadata field, explicitly write its name followed by a
        colon, a space, and its value.
        - Separate every metadata field using the exact separator " | ".
        - Leave a blank line between the image identifier, Morphology, and Metadata sections.
        - Do not add any additional sections or formatting.
        - Leave a blank line between candidates.

        MORPHOLOGY:

        Describe the visible structures, shapes, textures, and spatial
        organization using only the visual description provided in the
        retrieved context.

        METADATA:

        Report the following fields in exactly this order, using the exact
        field names shown below:

        Magnification
        Accelerating voltage
        Emission current
        Dwell time
        Working distance
        Scan mode
        Detector

        Format each field as "<field name>: <value>".

        Include every field when it is available in the retrieved context.
        If a field is not available, write "<field name>: Not available".

        Preserve stored values and units. Do not infer, estimate, or
        normalize metadata. Do not omit a field because it seems irrelevant.

        Do not compare candidates or claim that one is more relevant
        than another.

        Do not add other sections or introductory text.
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
class QueryMetadataExtractor:
    """
    Extract explicit metadata constraints from a natural-language query
    and convert valid constraints into Haystack/Qdrant filters.
    """
    def __init__(self):
        template = [
            ChatMessage.from_system(
                """
                You are part of an information retrieval system for Scanning Electron
                Microscopy (SEM) images.

                Your task is to extract metadata constraints explicitly expressed in
                a user's natural-language query and map them to the canonical fields
                and values defined in the supplied metadata schema.

                The metadata schema provides:
                - canonical metadata field names
                - field types and scientific descriptions
                - alternative terms for numeric fields
                - canonical units for numeric fields
                - allowed categorical values
                - descriptions and alternative terms for categorical values

                Use the scientific descriptions and dictionary terms to understand
                what the user means. The user does not need to use the canonical
                field name.

                Do NOT use general SEM knowledge to infer metadata that the user
                did not provide.

                ------------------------------------------------------------
                REQUIRED OUTPUT FORMAT
                ------------------------------------------------------------

                Return exactly one valid JSON object and nothing else.

                Each metadata constraint MUST be represented by a canonical field
                name at the top level. Its value MUST be an object containing
                "operator" and "value".

                Correct structure:

                {
                    "accelerating_voltage_kv": {
                        "operator": "~",
                        "value": 5
                    },
                    "detector": {
                        "operator": "==",
                        "value": "STEM"
                    }
                }

                Never put "operator" or "value" directly at the top level.
                Never return Markdown, code fences, comments, or explanations.

                If the query contains no metadata constraints, return exactly: {}

                ------------------------------------------------------------
                NUMERIC FIELDS
                ------------------------------------------------------------

                Numeric fields include:
                - magnification_x
                - accelerating_voltage_kv
                - emission_current_µa
                - dwell_time_µs
                - working_distance_mm

                Use the canonical field name and canonical unit defined in the
                metadata schema. Return numeric JSON values, not strings.

                Supported operators:

                ">=":
                    Use when the user specifies a lower bound, such as "at least",
                    "greater than", "above", or "no less than".

                "<=":
                    Use when the user specifies an upper bound, such as "at most",
                    "less than", "below", or "up to".

                "~":
                    Use for approximate values, such as "around", "about",
                    "roughly", or "approximately".
                    Also use it when the user gives a numeric value as a target
                    without specifying a comparison or range.

                "between":
                    Use when the user explicitly specifies a range with two bounds.
                    The value MUST be an array containing exactly two numbers: [low, high].

                Examples:

                "images acquired at around 5 kV"

                {
                    "accelerating_voltage_kv": {
                        "operator": "~",
                        "value": 5
                    }
                }

                "magnification greater than 2000x"

                {
                    "magnification_x": {
                        "operator": ">=",
                        "value": 2000
                    }
                }

                "working distance between 5 and 8 mm"

                {
                    "working_distance_mm": {
                        "operator": "between",
                        "value": [5, 8]
                    }
                }

                Preserve the meaning of the user's comparison. Do not replace an
                explicit lower bound, upper bound, or range with an approximate
                comparison.

                UNIT HANDLING:

                - Use the canonical unit specified in the schema.
                - Convert a supplied unit only when its meaning and conversion to
                the canonical unit are unambiguous.
                - Do not guess the unit when it is missing or ambiguous.
                - Do not invent additional numeric constraints.

                ------------------------------------------------------------
                CATEGORICAL FIELDS
                ------------------------------------------------------------

                Categorical fields are:
                - scan_mode
                - detector

                For each categorical constraint, map the user's wording to exactly
                one allowed canonical value in the metadata schema.

                The returned value MUST match the canonical value exactly,
                including its spelling, capitalization, spaces, punctuation,
                and any suffixes.

                Use the categorical value descriptions and dictionary terms to
                recognize alternative wording. However, do not return an alias
                when the schema defines a canonical value.

                Never invent a categorical value or return a value not listed in
                the schema.

                Examples:

                If the user asks for images acquired in wide-field mode, return:

                {
                    "scan_mode": {
                        "operator": "==",
                        "value": "WIDE FIELD"
                    }
                }

                If the user asks for images acquired using the STEM detector,
                return:

                {
                    "detector": {
                        "operator": "==",
                        "value": "STEM"
                    }
                }

                IMPORTANT: CATEGORICAL VALUES MUST BE PRESERVED AS COMPLETE STRINGS.

                If the wording cannot be mapped confidently to an allowed
                categorical value, omit that constraint rather than inventing
                a value. Other clearly specified constraints should still be
                returned.

                ------------------------------------------------------------
                MULTIPLE CONSTRAINTS
                ------------------------------------------------------------

                When the user specifies multiple metadata constraints, return
                each as a separate top-level field in the same JSON object.

                Example query:

                "Find images acquired at around 5 kV in wide-field mode using
                the STEM detector."

                Output:

                {
                    "accelerating_voltage_kv": {
                        "operator": "~",
                        "value": 5
                    },
                    "scan_mode": {
                        "operator": "==",
                        "value": "WIDE FIELD"
                    },
                    "detector": {
                        "operator": "==",
                        "value": "STEM"
                    }
                }

                Each field must have its own "operator" and "value" object.
                Do not combine different fields into one constraint.
                Do not omit a clearly specified valid constraint merely because
                another part of the query is ambiguous.

                ------------------------------------------------------------
                GENERAL RULES
                ------------------------------------------------------------

                1. Extract only metadata constraints explicitly stated or clearly
                requested by the user.

                2. Do not infer metadata from morphology, material, or general
                scientific knowledge.

                3. Use only canonical field names defined in the schema.

                4. Use only the supported numeric operators: >=, <=, ~, between.

                5. For categorical fields, always use operator "==" and an exact
                canonical value from the schema.

                6. For "between", return exactly two numeric values in ascending
                order. If the bounds are ambiguous, do not invent them.

                7. If the query contains no metadata constraints, return {}.

                8. If one constraint is invalid or ambiguous, omit that constraint
                while preserving other valid constraints.

                9. Return only valid JSON. Do not include Markdown fences,
                comments, explanations, or any text outside the JSON object.

                10. The Python application will validate the JSON and construct
                    the Qdrant filter. Your responsibility is to extract the
                    intended constraints faithfully.
                """
            ),
            ChatMessage.from_user(
                """
                Query:
                {{ query }}

                Metadata schema:
                {{ metadata_schema }}

                Extracted metadata:
                """
            ),
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
                model=GENERATION_MODEL_ID,
                api_key=get_vllm_secret(),
                api_base_url=API_URL,
                generation_kwargs={
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                    "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
                },
            )
        )
        self.pipeline.connect("builder", "llm")

    def build_condition(self, field: str, extracted: dict) -> dict | None:
        """Validate one extracted constraint and build its filter."""
        schema = METADATA_SCHEMA[field]
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

    @component.output_types(filters = dict[str, str])
    def run(self, query: str, metadata_schema: str):
        """Extract metadata and return a combined filter, if applicable."""
        result = self.pipeline.run({"builder": {"query": query, "metadata_schema": metadata_schema}})

        try:
            replies = result["llm"]["replies"]
            if not replies:
                return {"filters": None}

            metadata = json.loads(replies[0].text)

            log.info("QUERY: {}", query)
            log.info("EXTRACTED METADATA: {}", metadata)

            if not isinstance(metadata, dict):
                return {"filters": None}

            conditions = []

            for field, extracted in metadata.items():
                if field not in METADATA_SCHEMA:
                    continue

                if not isinstance(extracted, dict):
                    continue

                condition = self.build_condition(field, extracted)
                if condition is not None:
                    conditions.append(condition)

            log.info("GENERATED CONDITIONS: {}", conditions)

            if not conditions:
                return {"filters": None}

            return {"filters": {"operator": "AND", "conditions": conditions}}

        except Exception as exc:
            log.warning("Failed to extract query metadata: {}", exc)
            return {"filters": None}


@component
class QueryEmbedder:
    """
    Generate a Qwen3-VL embedding for a text query or uploaded image.

    When an image is present, the image is embedded directly. The query
    text is still passed separately to metadata extraction.
    """
    def __init__(self, model: str, api_base_url: str, api_key: str):
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
    def __init__(self, top_k: int = TOP_K, lambda_: float = MMR_LAMBDA):
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

        return {
            "documents": [documents[i] for i in selected]
        }


def render_image_gallery(documents: list[Document]) -> str:
    """Render retrieved image thumbnails in the response."""
    if not documents:
        return ""

    gallery = "\n\n**Candidate images:**\n"

    for index, doc in enumerate(documents, start=1):
        gallery += f"\n{index}. Image ID: `{doc.id}`\n\n"
        gallery += f"![SEM image {doc.id}]({THUMBNAIL_BASE_URL}/{doc.id}.png)\n"

    return gallery


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        document_store = get_document_store()

        # __________ RETRIEVAL PIPELINE __________
        self.retrieval_pipeline = Pipeline()

        self.retrieval_pipeline.add_component("query_embedder", QueryEmbedder(model=EMBED_MODEL_ID, api_base_url=API_URL, api_key=VLLM_API_KEY))
        self.retrieval_pipeline.add_component("metadata_extractor", QueryMetadataExtractor())
        self.retrieval_pipeline.add_component("retriever", QdrantEmbeddingRetriever(document_store=document_store, top_k=MMR_CANDIDATES, return_embedding=True))
        self.retrieval_pipeline.add_component("mmr", MMRReranker(top_k=TOP_K, lambda_=MMR_LAMBDA))

        self.retrieval_pipeline.connect("metadata_extractor.filters", "retriever.filters")
        self.retrieval_pipeline.connect("query_embedder.embedding", "retriever")
        self.retrieval_pipeline.connect("query_embedder.embedding", "mmr.query_embedding")
        self.retrieval_pipeline.connect("retriever.documents", "mmr.documents")

        # __________ GENERATION PIPELINE __________
        self.generation_pipeline = Pipeline()

        self.generation_pipeline.add_component("prompt_builder", ChatPromptBuilder(template=TEMPLATE, required_variables={"question", "documents"}))
        self.generation_pipeline.add_component("llm", VLLMChatGenerator(model=GENERATION_MODEL_ID, api_key=get_vllm_secret(), api_base_url=API_URL))
        self.generation_pipeline.add_component("answer_builder", AnswerBuilder())

        self.generation_pipeline.connect("prompt_builder", "llm")
        self.generation_pipeline.connect("llm", "answer_builder")

    def extract_query(self, messages: list[dict]) -> tuple[str, list[str]]:
        """Extract the latest user message and uploaded image URLs."""
        message = next((item for item in reversed(messages) if item.get("role") == "user"), None)

        if message is None:
            return "", []

        content = message.get("content", "")
        if isinstance(content, str):
            return content, []

        text = ""
        images = []

        for part in content:
            if part.get("type") == "text":
                text += part.get("text", "")

            elif part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url")
                if url:
                    images.append(url)

        return text, images

    def retrieve_documents(self, question: str, images: list[str]) -> list[Document]:
        """Run embedding, metadata filtering, retrieval, and MMR."""
        retrieval_run_args = {
            "metadata_extractor": {
                "query": question,
                "metadata_schema": METADATA_SCHEMA_DESCRIPTION,
            },
            "query_embedder": {
                "text": question,
                "image_data_urls": images,
            },
        }

        response = self.retrieval_pipeline.run(retrieval_run_args)
        documents = response.get("mmr", {}).get("documents", [])

        log.info("Retrieved {} documents for query: '{}'", len(documents), question)

        for document in documents:
            log.info("Retrieved document {} with metadata: {}", document.id, document.meta)

        return documents

    def run_chat_completion(self, model: str, messages: list[dict], body: dict) -> Union[str, Generator]:
        question, images = self.extract_query(messages)
        log.trace("Question: {}", question)

        # Stage 1: Retrieval
        documents = self.retrieve_documents(question=question, images=images)

        if not documents:
            return ("I couldn't find any SEM images matching the query and its metadata constraints.")

        # Stage 2: Generation
        generation_run_args = {
            "prompt_builder": {
                "question": question,
                "documents": documents,
            },
            "answer_builder": {
                "query": question,
            },
        }

        if body.get("stream", False):

            def on_generation_end(result: dict) -> str:
                return render_image_gallery(documents)

            return streaming_generator(
                pipeline=self.generation_pipeline,
                pipeline_run_args=generation_run_args,
                on_pipeline_end=on_generation_end,
            )

        response = self.generation_pipeline.run(generation_run_args)
        answers = response.get("answer_builder", {}).get("answers", [])

        if not answers:
            return "Sorry, I couldn't generate an answer."

        return answers[0].data + render_image_gallery(documents)
