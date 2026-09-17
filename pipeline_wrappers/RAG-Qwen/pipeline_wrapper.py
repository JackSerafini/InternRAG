"""
Hayhooks PipelineWrapper for the QWEN RAG retrieval pipeline.
"""
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

THUMBNAIL_BASE_URL = os.getenv("THUMBNAIL_BASE_URL", "https://llm-rag.dev.rd.areasciencepark.it/rag-images")

# __________ MANUAL CONFIGURATION __________ #
GENERATION_MODEL_ID = "google/gemma-4-26B-A4B-it"
EMBED_MODEL_ID = "Qwen/Qwen3-VL-Embedding-8B"
EMBEDDING_DIM = 4096

MMR_CANDIDATES = 50
TOP_K = 5

QDRANT_COLLECTION = "SEM_qwen"

INSTRUCTION = "Represent the user's input."


if not VLLM_API_KEY:
    raise RuntimeError("VLLM_API_KEY is not set.")


# __________ METADATA SCHEMA __________
# This is the single source of truth for query metadata extraction.
# 
# The ingestion pipeline stores these canonical field names in Qdrant.
# The LLM receives:
#   - field descriptions
#   - alternative/dictionary terms
#   - units for numeric fields
#   - allowed values and their descriptions for categorical fields

# Right now, all fields are taken relative to the value passed, ±10%
# TODO: tune this -> some might need an absolute range (e.g., ±10% of a very small value will practically be exact)
METADATA_SCHEMA = {
    # __________ Numeric fields __________
    "pixel_size_nm": {
        "type": "numeric",
        "description": (
            "Physical spatial sampling represented by one image pixel. "
            "It expresses the real-space scale of the SEM image and allows "
            "images acquired at different spatial scales to be compared."
        ),
        "dictionary_terms": [
            "pixel size",
            "image pixel size",
            "pixel dimension",
            "nm per pixel",
            "nm/pixel",
            "nanometers per pixel",
            "nanometres per pixel",
            "um per pixel",
            "µm per pixel",
            "micrometers per pixel",
            "micrometres per pixel",
            "spatial sampling",
            "pixel sampling",
            "sampling resolution",
        ],
        "unit": "nm/pixel",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "magnification_x": {
        "type": "numeric",
        "description": (
            "Nominal SEM magnification used when the image was acquired."
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
        "unit": "x",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "accelerating_voltage_kv": {
        "type": "numeric",
        "description": (
            "Electron beam accelerating voltage, commonly reported as EHT. "
            "It influences electron penetration, interaction volume, "
            "surface sensitivity, charging behaviour and signal generation."
        ),
        "dictionary_terms": [
            "accelerating voltage",
            "acceleration voltage",
            "EHT",
            "beam voltage",
            "electron beam voltage",
            "electron voltage",
            "high tension",
            "high voltage",
            "operating voltage",
            "kV",
            "kilovolts",
            "kilovolt",
        ],
        "unit": "kV",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "working_distance_mm": {
        "type": "numeric",
        "description": (
            "SEM working distance associated with the specimen-to-objective "
            "imaging geometry. It influences imaging conditions such as depth "
            "of field, resolution and detector geometry."
        ),
        "dictionary_terms": [
            "working distance",
            "WD",
            "work distance",
            "working dist",
            "working-distance",
            "focus distance",
            "sample distance",
            "specimen distance",
        ],
        "unit": "mm",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "brightness_percent": {
        "type": "numeric",
        "description": (
            "Instrument brightness setting applied during acquisition. "
            "It controls the displayed or saved signal intensity level."
        ),
        "dictionary_terms": [
            "brightness",
            "brightness level",
            "image brightness",
            "brightness setting",
            "brightness percentage",
            "bright",
            "intensity level",
        ],
        "unit": "%",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "contrast_percent": {
        "type": "numeric",
        "description": (
            "Instrument contrast setting applied during acquisition. "
            "It controls the separation and dynamic range of intensities "
            "represented in the SEM image."
        ),
        "dictionary_terms": [
            "contrast",
            "contrast level",
            "image contrast",
            "contrast setting",
            "contrast percentage",
            "dynamic range",
            "intensity contrast",
        ],
        "unit": "%",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "scan_speed_setting": {
        "type": "numeric",
        "description": (
            "Instrument-specific scan speed setting controlling how rapidly "
            "the electron beam scans the image. It is an ordinal acquisition "
            "setting rather than a physical time unless separately calibrated."
        ),
        "dictionary_terms": [
            "scan speed",
            "scan rate",
            "scanrate",
            "scanning speed",
            "scanning rate",
            "scan speed setting",
            "scan setting",
            "acquisition speed",
            "raster speed",
        ],
        "unit": "setting",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "frame_average_count": {
        "type": "numeric",
        "description": (
            "Number of image frames averaged together during acquisition "
            "to reduce random noise and improve signal-to-noise ratio."
        ),
        "dictionary_terms": [
            "frame averaging",
            "frame average",
            "frame average count",
            "frame averaging count",
            "frames averaged",
            "number of frames averaged",
            "frames to average",
            "average frames",
            "frame count",
        ],
        "unit": "count",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    "line_average_count": {
        "type": "numeric",
        "description": (
            "Number of repeated scan lines averaged during acquisition "
            "to reduce noise and improve signal stability."
        ),
        "dictionary_terms": [
            "line averaging",
            "line average",
            "line average count",
            "line averaging count",
            "lines averaged",
            "number of lines averaged",
            "lines to average",
            "average lines",
        ],
        "unit": "count",
        "filter": {
            "type": "range",
            "tolerance": 0.10,
            "tolerance_type": "relative",
        },
    },

    # __________ Categorical fields __________
    "category": {
        "type": "categorical",
        "description": (
            "Human-assigned SEM morphology category from the annotated "
            "dataset described by Aversa et al. The categories were defined "
            "mainly from the dominant shape, structure and dimensionality "
            "of the imaged object."
        ),
        "values": {
            "Porous_Sponge": {
                "description": (
                    "SEM images assigned to the porous sponge category, "
                    "characterized by a porous or sponge-like morphology."
                ),
                "dictionary_terms": [
                    "porous sponge",
                    "porous sponges",
                    "sponge-like",
                    "sponge like",
                ],
            },
            "Patterned_surface": {
                "description": (
                    "SEM images of surfaces containing organized, repeated "
                    "or lithographically defined patterns or structures."
                ),
                "dictionary_terms": [
                    "patterned surface",
                    "patterned surfaces",
                    "surface pattern",
                    "surface patterns",
                    "patterned",
                ],
            },
            "Particles": {
                "description": (
                    "Zero-dimensional particle-like objects that may be "
                    "individually dispersed or grouped into clustered structures."
                ),
                "dictionary_terms": [
                    "particle",
                    "particles",
                    "nanoparticle",
                    "nanoparticles",
                    "nano particle",
                    "nano particles",
                ],
            },
            "Films_Coated_Surface": {
                "description": (
                    "Two-dimensional films or coatings on a surface, including "
                    "surfaces with different degrees of roughness or particle coverage."
                ),
                "dictionary_terms": [
                    "film",
                    "films",
                    "coated surface",
                    "coated surfaces",
                    "coating",
                    "coatings",
                    "thin film",
                    "thin films",
                ],
            },
            "Powder": {
                "description": (
                    "SEM images assigned to the powder category in the annotated dataset."
                ),
                "dictionary_terms": [
                    "powder",
                    "powders",
                    "powder sample",
                    "powder samples",
                ],
            },
            "Tips": {
                "description": (
                    "Tip-like structures, including images commonly associated "
                    "with atomic force microscopy probe tips."
                ),
                "dictionary_terms": [
                    "tip",
                    "tips",
                    "AFM tip",
                    "AFM tips",
                    "probe tip",
                    "probe tips",
                ],
            },
            "Nanowires": {
                "description": (
                    "One-dimensional nanowire structures. In the dataset hierarchy, "
                    "nanowires can include individual, few, entangled or forest-like arrangements."
                ),
                "dictionary_terms": [
                    "nanowire",
                    "nanowires",
                    "nano wire",
                    "nano wires",
                ],
            },
            "Biological": {
                "description": (
                    "SEM images of biological samples grouped into the Biological "
                    "category of the annotated dataset."
                ),
                "dictionary_terms": [
                    "biological",
                    "biological sample",
                    "biological samples",
                    "bio sample",
                    "bio samples",
                ],
            },
            "MEMS_devices_and_electrodes": {
                "description": (
                    "Microelectromechanical devices, electrodes and related "
                    "microfabricated structures, typically associated with lithographic fabrication."
                ),
                "dictionary_terms": [
                    "MEMS",
                    "MEMS device",
                    "MEMS devices",
                    "electrode",
                    "electrodes",
                    "microelectromechanical",
                    "microelectromechanical system",
                    "microelectromechanical systems",
                    "microdevice",
                    "microdevices",
                ],
            },
            "Fibres": {
                "description": (
                    "One-dimensional fibrous structures assigned to the dedicated "
                    "Fibres category of the annotated dataset."
                ),
                "dictionary_terms": [
                    "fibre",
                    "fibres",
                    "fiber",
                    "fibers",
                    "fibrous",
                ],
            },
        },
    },

    "detector": {
        "type": "categorical",
        "description": (
            "Detector or signal channel used to form the SEM image. "
            "Detector choice affects the type of electron signal recorded "
            "and therefore the appearance and scientific information represented in the image."
        ),
        "values": {
            "InLens": {
                "description": (
                    "In-lens detector signal used for SEM image formation. "
                    "The instrument described in the dataset paper includes "
                    "a high-efficiency in-lens detector."
                ),
                "dictionary_terms": [
                    "InLens",
                    "in lens",
                    "in-lens",
                    "inlens",
                    "in lens detector",
                    "in-lens detector",
                ],
            },
            "SE2": {
                "description": (
                    "Secondary-electron detector channel labelled SE2 "
                    "in the instrument metadata."
                ),
                "dictionary_terms": [
                    "SE2",
                    "se2",
                    "secondary electron",
                    "secondary electrons",
                    "secondary electron detector",
                    "SE detector",
                ],
            },
            "HDAsB": {
                "description": (
                    "Backscattered-electron detector channel labelled HDAsB "
                    "in the instrument metadata."
                ),
                "dictionary_terms": [
                    "HDAsB",
                    "hdasb",
                    "backscatter detector",
                    "backscattered electron detector",
                    "backscattered electrons",
                    "BSE detector",
                    "BSE",
                ],
            },
        },
    },
}

# __________ METADATA SCHEMA HELPERS __________
def build_metadata_schema_description() -> str:
    """
    Convert the internal metadata schema into JSON for the metadata
    extraction LLM.

    The schema contains all information the LLM needs to map natural
    language to canonical metadata fields and values.
    """
    return json.dumps(METADATA_SCHEMA, indent=2, ensure_ascii=False)

METADATA_SCHEMA_DESCRIPTION = build_metadata_schema_description()


TEMPLATE = [
    ChatMessage.from_system(
        """
        You are an expert in Scanning Electron Microscopy (SEM), helping a
        researcher review SEM image candidates that have already been ranked
        by visual similarity to their query.

        The ranking was performed by the retrieval system, not by you.
        Do not assign relevance scores, rank candidates, or claim to judge
        how well an image matches the query.

        The actual images will be shown to the researcher separately.

        For each retrieved candidate, produce a concise summary.

        OUTPUT FORMAT:

        Each candidate must follow exactly this format:

        **Image <ID>**

        - **Morphology:** <brief description>

        - **Metadata:** <metadata fields>

        FORMATTING RULES:

        - Always write the image identifier in bold as **Image <ID>**.
        - Always write **Morphology:** and **Metadata:** in bold.
        - Do not use bullet points for Morphology or Metadata.
        - Put the complete metadata on a single line.
        - Separate every metadata field using the exact separator " | ".
        - Do not use commas or semicolons as separators between metadata fields.
        - Do not put each metadata field on a separate line.
        - Leave a blank line between the image identifier, Morphology, and
          Metadata sections.
        - Do not add any additional sections or formatting.

        MORPHOLOGY:

        Briefly describe the visible structures, shapes, textures, and spatial
        organization using only the morphology description provided in the
        retrieved context.

        METADATA:

        Report the following metadata fields, in this exact order:

        Category
        Detector
        Pixel size
        Magnification
        Accelerating voltage
        Working distance
        Brightness
        Contrast
        Scan Speed
        Frame Average
        Line Average

        Include every field when it is available in the retrieved context.
        If a field is not available, write "Not available".

        Do not omit a metadata field because you consider it irrelevant to
        the query.

        Do not invent, infer, or estimate metadata.

        Preserve the values and units provided in the retrieved context.
        Do not modify or normalize them.

        Do not compare candidates with each other and do not state which
        candidate is better or more relevant.

        Retrieved context is the only source of information. Do not use
        external knowledge to fill missing information.
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
class QueryMetadataExtractor():
    """
    Extract metadata constraints from a natural-language query.

    The LLM is responsible for mapping the user's wording to canonical
    metadata fields and categorical values.

    Python is responsible for validating the result and converting it
    into a Qdrant filter.
    """
    def __init__(self):
        template = [
            ChatMessage.from_system(
                """
                You are part of an information system that extracts SEM metadata
                constraints from natural-language user queries.

                Your task is to identify metadata constraints explicitly provided by
                the user and map them to the canonical metadata fields and values
                defined in the supplied metadata schema.

                The metadata schema contains:
                - canonical field names
                - field types
                - scientific descriptions
                - alternative/dictionary terms
                - units for numeric fields
                - allowed values for categorical fields
                - alternative terms and descriptions for categorical values

                Use the scientific descriptions and dictionary terms to understand
                what the user means. The user does not need to use the canonical
                field name.

                Do NOT use general SEM knowledge to infer metadata that the user
                did not provide.

                ------------------------------------------------------------
                REQUIRED OUTPUT FORMAT
                ------------------------------------------------------------

                The output MUST always be a single JSON object.

                Each metadata field MUST be a top-level key in the JSON object.

                The value associated with each field MUST be an object containing:
                - "operator"
                - "value"

                The canonical metadata field name MUST be used as the top-level key.

                The keys "operator" and "value" MUST NEVER appear directly at
                the top level of the JSON object.

                For example, if the canonical field is "category", the correct
                structure is:

                {
                    "category": {
                        "operator": "==",
                        "value": "Porous_Sponge"
                    }
                }

                The following structure is INVALID:

                {
                    "operator": "==",
                    "value": "Porous_Sponge"
                }

                ------------------------------------------------------------
                NUMERIC FIELDS
                ------------------------------------------------------------

                For numeric fields, return:

                {
                    "<canonical_field_name>": {
                        "operator": "<operator>",
                        "value": <numeric value>
                    }
                }

                Supported operators:

                ">=": Greater than or equal to the specified value.

                "<=": Less than or equal to the specified value.

                "~": Approximately equal to the specified value.

                Use "~" when the user says:
                - around
                - about
                - roughly
                - approximately

                Also use "~" when the user gives a numeric value that sounds
                like an exact desired value without specifying an explicit
                comparison or range.

                "between": Use this when the user explicitly gives a range with two bounds.

                    The value MUST be an array:

                    [low, high]

                Examples:

                User:
                "images with pixel size around 100 nm"

                Output:

                {
                    "pixel_size_nm": {
                        "operator": "~",
                        "value": 100
                    }
                }

                User:
                "images with pixel size greater than 100 nm"

                Output:

                {
                    "pixel_size_nm": {
                        "operator": ">=",
                        "value": 100
                    }
                }

                User:
                "images with pixel size up to 100 nm"

                Output:

                {
                    "pixel_size_nm": {
                        "operator": "<=",
                        "value": 100
                    }
                }

                User:
                "images with pixel size between 80 and 120 nm"

                Output:

                {
                    "pixel_size_nm": {
                        "operator": "between",
                        "value": [80, 120]
                    }
                }

                Do not convert units unless the query explicitly provides a unit
                that can be safely interpreted.

                If the user provides a unit, use the canonical numeric field
                and represent the numeric value consistently with the metadata
                schema.

                ------------------------------------------------------------
                CATEGORICAL FIELDS
                ------------------------------------------------------------

                For categorical fields, map the user's wording to exactly one
                of the allowed canonical values defined in the metadata schema.

                The canonical categorical value MUST be used.

                The categorical field MUST be the top-level JSON key.

                The structure MUST be:

                {
                    "<canonical_field_name>": {
                        "operator": "==",
                        "value": "<allowed canonical value>"
                    }
                }

                Never return a categorical value that is not present in the
                allowed values defined by the schema.

                Never invent a categorical value.

                Example:

                Suppose the schema contains:

                category:
                    Porous_Sponge:
                        dictionary terms:
                            porous sponge
                            porous sponges
                            sponge
                            sponge-like structure

                Then the query:

                "show SEM images that are Porous Sponges"

                MUST produce:

                {
                    "category": {
                        "operator": "==",
                        "value": "Porous_Sponge"
                    }
                }

                It MUST NOT produce:

                {
                    "operator": "==",
                    "value": "Porous_Sponge"
                }

                Another example:

                Suppose the schema contains:

                detector:
                    SE2:
                        dictionary terms:
                            secondary electron
                            secondary electron detector
                            SE detector

                Then:

                "images acquired with a secondary electron detector"

                MUST produce:

                {
                    "detector": {
                        "operator": "==",
                        "value": "SE2"
                    }
                }

                ------------------------------------------------------------
                MULTIPLE METADATA CONSTRAINTS
                ------------------------------------------------------------

                If the user provides multiple metadata constraints, include all
                of them as separate top-level fields in the same JSON object.

                For example:

                User:
                "show SEM images that are Porous Sponges with 100 nm pixel size"

                Output:

                {
                    "category": {
                        "operator": "==",
                        "value": "Porous_Sponge"
                    },
                    "pixel_size_nm": {
                        "operator": "~",
                        "value": 100
                    }
                }

                Another example:

                User:
                "show Porous Sponge images acquired at 10 kV with a 100 nm pixel size"

                Output:

                {
                    "category": {
                        "operator": "==",
                        "value": "Porous_Sponge"
                    },
                    "accelerating_voltage_kv": {
                        "operator": "~",
                        "value": 10
                    },
                    "pixel_size_nm": {
                        "operator": "~",
                        "value": 100
                    }
                }

                Each constraint MUST have its own canonical field name.

                Do not combine multiple constraints into a single object.

                ------------------------------------------------------------
                GENERAL RULES
                ------------------------------------------------------------

                1. Only include a metadata field if the query explicitly provides
                or clearly implies its value.

                2. Do not infer metadata from general SEM knowledge.

                3. Do not infer metadata from the morphology described by the user.

                4. Do not invent canonical field names.

                5. Do not invent categorical values.

                6. For categorical fields, the value MUST exactly match one of the
                allowed canonical values in the supplied schema.

                7. For numeric fields, use only the supported operators:
                >=, <=, ~, between.

                8. For "between", the value MUST contain exactly two numeric values:
                [low, high]

                9. Preserve the meaning of the user's constraint. Do not silently
                change a comparison into another comparison.

                10. If the user does not specify a metadata constraint, do not
                    invent one.

                11. If no metadata fields are present in the query, return exactly:

                {}

                12. The output must contain ONLY valid JSON.

                13. Do not include Markdown code fences.

                14. Do not include explanations, comments, or additional text.

                15. The top-level JSON object MUST contain canonical metadata field
                    names, never "operator" or "value".

                ------------------------------------------------------------
                FINAL EXAMPLES
                ------------------------------------------------------------

                Query:
                "Find spherical particles."

                Output:

                {}

                Query:
                "show images that are Porous Sponges"

                Output:

                {
                    "category": {
                        "operator": "==",
                        "value": "Porous_Sponge"
                    }
                }

                Query:
                "show images with 100 nm pixel size"

                Output:

                {
                    "pixel_size_nm": {
                        "operator": "~",
                        "value": 100
                    }
                }

                Query:
                "show Porous Sponge images with 100 nm pixel size"

                Output:

                {
                    "category": {
                        "operator": "==",
                        "value": "Porous_Sponge"
                    },
                    "pixel_size_nm": {
                        "operator": "~",
                        "value": 100
                    }
                }

                Query:
                "show images with pixel size between 50 and 100 nm and category Powder"

                Output:

                {
                    "pixel_size_nm": {
                        "operator": "between",
                        "value": [50, 100]
                    },
                    "category": {
                        "operator": "==",
                        "value": "Powder"
                    }
                }

                Remember:

                - Top-level keys = canonical metadata field names.
                - Nested "operator" = comparison operator.
                - Nested "value" = extracted value.
                - Never put "operator" or "value" directly at the top level.
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
                required_variables={"query", "metadata_schema"}
            )
        )
        self.pipeline.add_component(
            "llm", 
            VLLMChatGenerator(
                model=GENERATION_MODEL_ID, 
                api_key=get_vllm_secret(), 
                api_base_url=API_URL, 
                generation_kwargs={"response_format": {"type": "json_object"}}
            )
        )
        self.pipeline.connect("builder", "llm")

    def build_condition(self, field: str, extracted: dict):
        """
        Validate one extracted metadata field and convert it into
        a Qdrant filter condition.
        """
        schema = METADATA_SCHEMA[field]
        field_type = schema["type"]

        operator = extracted.get("operator")
        value = extracted.get("value")

        # __________ Categorical fields __________
        if field_type == "categorical":
            if operator != "==":
                return None

            if not isinstance(value, str):
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

        valid_numeric_operators = {
            ">=",
            "<=",
            "~",
            "between",
        }

        if operator not in valid_numeric_operators:
            return None

        # __________ Numeric range __________
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
                    {
                        "field": f"meta.{field}",
                        "operator": ">=",
                        "value": low,
                    },
                    {
                        "field": f"meta.{field}",
                        "operator": "<=",
                        "value": high,
                    },
                ],
            }

        # __________ Numeric value __________
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        # __________ Approximate numeric value __________
        if operator == "~":
            filter_config = schema.get("filter", {})

            tolerance = filter_config.get("tolerance", 0.10)

            tolerance_type = filter_config.get("tolerance_type", "relative")

            if tolerance_type == "relative":
                delta = abs(value) * tolerance
            else:
                delta = tolerance

            return {
                "operator": "AND",
                "conditions": [
                    {
                        "field": f"meta.{field}",
                        "operator": ">=",
                        "value": value - delta,
                    },
                    {
                        "field": f"meta.{field}",
                        "operator": "<=",
                        "value": value + delta,
                    },
                ],
            }

        # ">=", "<=" map directly onto Qdrant's own operator strings
        return {
            "field": f"meta.{field}",
            "operator": operator,
            "value": value,
        }

    @component.output_types(filters = dict[str, str])
    def run(self, query: str, metadata_schema: str):
        """
        Extract metadata from the query and convert it into a Qdrant
        filter.

        Invalid or hallucinated fields/values are silently discarded.
        If nothing valid remains, no filter is returned.
        """
        result = self.pipeline.run({'builder': {'query': query, 'metadata_schema': metadata_schema}})
        try:
            replies = result["llm"]["replies"]

            if not replies:
                return {"filters": None}

            metadata = json.loads(replies[0].text)

            log.info(f"QUERY: {query}")
            log.info(f"EXTRACTED METADATA: {metadata}")

            if not isinstance(metadata, dict):
                return {"filters": None}

            conditions = []

            for field, extracted in metadata.items():

                # Prevent hallucinated field names.
                if field not in METADATA_SCHEMA:
                    continue

                # Each field must contain an extraction object.
                if not isinstance(extracted, dict):
                    continue

                condition = self.build_condition(field, extracted)

                if condition is not None:
                    conditions.append(condition)

            log.info(f"GENERATED CONDITIONS: {conditions}")

            if not conditions:
                return {"filters": None}

            return {"filters": {"operator": "AND", "conditions": conditions}}

        except Exception as exc:
            log.warning("Failed to extract query metadata: {}", exc)
            return {"filters": None}


@component
class QueryEmbedder():
    """
    Generate a Qwen3-VL embedding from either text or an image.

    If an image is provided, the image is embedded directly.
    Otherwise the textual query is embedded.
    """
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


@component
class MMRReranker():
    def __init__(self, top_k: int = 5, lambda_: float = 0.8):
        self.top_k = top_k
        self.lambda_ = lambda_

    @component.output_types(documents=list[Document])
    def run(
        self,
        query_embedding: list[float],
        documents: list[Document],
    ):
        if not documents:
            return {"documents": []}

        if len(documents) <= self.top_k:
            return {"documents": documents}

        # Turn embeddings into NumPy arrays
        query = np.asarray(query_embedding, dtype=np.float32)
        embeddings = np.asarray([document.embedding for document in documents], dtype=np.float32)

        # Normalize embeddings for cosine similarity
        query = query / np.linalg.norm(query)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Similarity between query and each candidate -> array with [sim(query, A), sim(query, B), ...]
        query_similarities = embeddings @ query

        # Pairwise candidate similarities -> 50x50 matrix with how similar every candidate is to every other candidate
        candidate_similarities = embeddings @ embeddings.T

        selected = [] # list of selected images' indexes
        remaining = list(range(len(documents))) # list of indexes [0, 1, 2, ...]

        # First result: index of the most similar image to query
        first = int(np.argmax(query_similarities))
        selected.append(first) # [0]
        remaining.remove(first)

        while len(selected) < self.top_k and remaining:
            mmr_scores = []

            for candidate in remaining:
                # Take the relevance to the query for each candidate
                relevance = query_similarities[candidate]

                # Compute the max similarity between already selected images and each candidate
                redundancy = np.max(candidate_similarities[candidate, selected])

                # Compute MMR for each candidate and add the tuple [mrr_score, candidate_index] to the list
                mmr = self.lambda_ * relevance - (1 - self.lambda_) * redundancy
                mmr_scores.append((mmr, candidate))

            _, best_candidate = max(mmr_scores)

            selected.append(best_candidate)
            remaining.remove(best_candidate)

        return {
            "documents": [documents[i] for i in selected]
        }


def render_image_gallery(documents) -> str:
    """
    Render the retrieved candidates as inline images so the researcher can
    actually see what's being discussed, not just read a paraphrase of it.
    """
    if not documents:
        return ""

    gallery = "\n\n**Candidate images:**\n"

    for idx, doc in enumerate(documents, start=1):
        gallery += f"\n{idx}. Image ID: `{doc.id}`\n"
        gallery += f"\n![SEM image {doc.id}]({THUMBNAIL_BASE_URL}/{doc.id}.png)\n"
    
    return gallery


class PipelineWrapper(BasePipelineWrapper):
    def setup(self) -> None:
        document_store = get_document_store()

        # __________ RETRIEVAL PIPELINE __________
        self.retrieval_pipeline = Pipeline()

        self.retrieval_pipeline.add_component("query_embedder", QueryEmbedder(model=EMBED_MODEL_ID, api_base_url=API_URL, api_key=VLLM_API_KEY))
        self.retrieval_pipeline.add_component("metadata_extractor", QueryMetadataExtractor())
        self.retrieval_pipeline.add_component("retriever", QdrantEmbeddingRetriever(document_store=document_store, top_k=MMR_CANDIDATES, return_embedding=True))
        self.retrieval_pipeline.add_component("mmr", MMRReranker(top_k=TOP_K, lambda_=0.8))

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

    def extract_query(self, messages: list[dict]):
        """
        Extract the latest user text and any image URLs from the
        OpenWebUI message structure.
        """
        msg = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        if msg is None:
            return "", []

        content = msg.get("content", "")
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

    def retrieve_documents(self, question: str, images: list[str]):
        """
        Execute the retrieval stage synchronously.

        This is intentionally separated from generation so that we can
        detect zero-result retrievals before invoking the LLM.
        """
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

        # documents = (response.get("retriever", {}).get("documents", []))
        documents = (response.get("mmr", {}).get("documents", []))

        log.info(f"Retrieved {len(documents)} documents for query: '{question}'")

        for document in documents:
            log.info(f"Retrieved document {document.id} with metadata: {document.meta}")

        return documents

    def run_chat_completion(self, model: str, messages: list[dict], body: dict) -> Union[str, Generator]:
        question, images = self.extract_query(messages)
        log.trace("Question: {}", question)

        # __________ Stage 1: Retrieval __________
        # This ALWAYS happens synchronously, even for streaming requests
        documents = self.retrieve_documents(question=question, images=images)

        # Zero-result handling
        # This happens BEFORE the generation pipeline is started.
        if not documents:
            return ("I couldn't find any SEM images matching all the requested criteria.")

        # __________ Stage 2: Generation __________
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

        # __________ Non-streaming generation __________
        response = self.generation_pipeline.run(generation_run_args)

        answers = response.get("answer_builder", {}).get("answers", [])
        if not answers:
            return "Sorry, I couldn't generate an answer."

        return answers[0].data + render_image_gallery(answers[0].documents)
