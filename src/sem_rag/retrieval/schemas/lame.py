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
            "A value may identify one detector or a comma-separated combination "
            "of detectors. The complete stored value is preserved for exact "
            "metadata filtering."
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
            "Axial, MD, E-T": {
                "description": "Combined detector configuration recorded as Axial, MD, E-T.",
                "dictionary_terms": [
                    "Axial, MD, E-T",
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
            "E-T, Axial": {
                "description": "Combined detector configuration recorded as E-T, Axial.",
                "dictionary_terms": [
                    "E-T, Axial",
                ],
            },
            "E-T, LE BSE": {
                "description": "Combined detector configuration recorded as E-T, LE BSE.",
                "dictionary_terms": [
                    "E-T, LE BSE",
                ],
            },
            "E-T, LE BSE, Axial (BSE)": {
                "description": (
                    "Combined detector configuration recorded as "
                    "E-T, LE BSE, Axial (BSE)."
                ),
                "dictionary_terms": [
                    "E-T, LE BSE, Axial (BSE)",
                ],
            },
            "E-T, MD": {
                "description": "Combined detector configuration recorded as E-T, MD.",
                "dictionary_terms": [
                    "E-T, MD",
                ],
            },
            "E-T, MD, Axial": {
                "description": "Combined detector configuration recorded as E-T, MD, Axial.",
                "dictionary_terms": [
                    "E-T, MD, Axial",
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
            "TE BF": {
                "description": "Detector configuration recorded as TE BF.",
                "dictionary_terms": [
                    "TE BF",
                    "TE-BF",
                    "TEBF",
                ],
            },
            "TE DF": {
                "description": "Detector configuration recorded as TE DF.",
                "dictionary_terms": [
                    "TE DF",
                    "TE-DF",
                    "TEDF",
                ],
            },
            "TE DF #2": {
                "description": "Detector configuration recorded as TE DF #2.",
                "dictionary_terms": [
                    "TE DF #2",
                    "TE-DF #2",
                ],
            },
            "TE HADF": {
                "description": "Detector configuration recorded as TE HADF.",
                "dictionary_terms": [
                    "TE HADF",
                    "TE-HADF",
                    "TEHADF",
                ],
            },
        },
    },
}


EXTRACTION_SYSTEM_PROMPT = """
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
        "value": "TE BF"
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

If the user asks for images acquired using the TE BF detector,
return:

{
    "detector": {
        "operator": "==",
        "value": "TE BF"
    }
}

IMPORTANT: CATEGORICAL VALUES MUST BE PRESERVED AS COMPLETE STRINGS.

Some detector values contain spaces, punctuation, or multiple
comma-separated detector labels. Examples include:
- "TE BF"
- "LE BSE"
- "Axial (BSE)"
- "E-T, MD"
- "E-T, Axial"
- "E-T, LE BSE, Axial (BSE)"

Treat every complete value listed in the schema as one categorical
value. Never split a canonical value on whitespace or commas.
Never shorten a value to its first word or silently reorder its
components.

A request for one detector label does not automatically mean that
a combined detector configuration should be selected. Return the
exact canonical configuration only when the user's wording
identifies that configuration. Do not infer component matching.

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
the TE BF detector."

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
        "value": "TE BF"
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