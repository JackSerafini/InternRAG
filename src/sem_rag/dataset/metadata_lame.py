import configparser
from pathlib import Path


NUMERIC_FIELDS = [
    "magnification_x",
    "accelerating_voltage_kv",
    "emission_current_µa",
    "dwell_time_µs",
    "working_distance_mm",
]

CATEGORICAL_FIELDS = [
    "scan_mode",
    "detector",
]

# Canonical field: (section, source key, conversion factor)
NUMERIC_FIELD_MAP = {
    "magnification_x": ("MAIN", "Magnification", 1.0),
    "accelerating_voltage_kv": ("SEM", "AcceleratorVoltage", 1e-3),
    "emission_current_µa": ("SEM", "EmissionCurrent", 1e6),
    "dwell_time_µs": ("SEM", "DwellTime", 1e6),
    "working_distance_mm": ("SEM", "WD", 1e3),
}

# Canonical field: (section, source key)
CATEGORICAL_FIELD_MAP = {
    "scan_mode": ("SEM", "ScanMode"),
    "detector": ("SEM", "Detector"),
}

FIELD_UNITS = {
    "magnification_x": "X",
    "accelerating_voltage_kv": "kV",
    "emission_current_µa": "µA",
    "dwell_time_µs": "µs",
    "working_distance_mm": "mm",
}


def normalize_detector(value: str | None) -> str | None:
    """Map all transmitted-electron channels (TE BF, TE DF, TE DF #2, TE HADF) to STEM."""
    if value is None:
        return None
    if value.split()[0] == "TE":
        return "STEM"
    
    return value


def load_hdr_metadata(hdr_path: str | Path) -> dict:
    """
    Load and normalize the relevant metadata from a SEM .hdr file.

    Numeric values are converted to their canonical units using
    `NUMERIC_FIELD_MAP` and `FIELD_UNITS`. Categorical values are
    stripped of leading and trailing whitespace. Missing or invalid
    values are represented as `None`.

    Args:
        hdr_path: Path to the .hdr file to read.

    Returns:
        A dictionary mapping canonical metadata field names to their
        normalized values. Numeric fields are stored as floats, with
        corresponding `<field>_unit` entries containing unit strings.
        Categorical fields are stored as strings. Missing or invalid
        values are stored as `None`.
    """
    hdr_path = Path(hdr_path)

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str # preserve key capitalization

    with hdr_path.open("r", encoding="utf-8-sig") as file:
        parser.read_file(file)

    metadata = {}

    # Numeric fields and unit conversions
    for field, (section, key, factor) in NUMERIC_FIELD_MAP.items():
        raw_value = parser.get(section, key, fallback=None)

        try:
            metadata[field] = float(raw_value) * factor if raw_value is not None and raw_value.strip() else None
        except ValueError:
            metadata[field] = None

        metadata[f"{field}_unit"] = FIELD_UNITS[field]

    # Categorical fields
    for field, (section, key) in CATEGORICAL_FIELD_MAP.items():
        value = parser.get(section, key, fallback=None)

        metadata[field] = value.strip() if value and value.strip() else None

    metadata["detector"] = normalize_detector(metadata["detector"])

    return metadata
