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

EXTRACTION_SYSTEM_PROMPT = """
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