# NOTE: in this script `object` will be used instead of `str` because JSON fields can contain `False`, which would create problems
import re

_CATEGORY_PATTERN = re.compile(r"=\s*(.*?)\s*$")

# Matches: "<label> = <number> <unit>" e.g. "WD = 3.198 mm"
_NUM_PATTERN = re.compile(
    r"=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([^\s=]*)\s*$"
)

_COMPUTED_PIXEL_SIZE_PATTERN = re.compile(
    r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(nm|µm|um|pm)\s*$",
    re.IGNORECASE
)

_MAGNIFICATION_PATTERN = re.compile(
    r"Mag\s*=\s*([0-9]*\.?[0-9]+)\s*(K)?\s*X",
    re.IGNORECASE,
)


_PIXEL_SIZE_UNIT_TO_NM = {
    "nm": 1.0,
    "µm": 1000.0,
    "um": 1000.0,
    "pm": 0.001,
}


def parse_category(raw_string: object) -> str | None:
    """
    Extract a categorical value from a SEM metadata string.

    The function expects metadata in the form ``"<label> = <value>"``.

    Args:
        raw_string: Raw metadata value to parse.

    Returns:
        The extracted categorical value, or ``None`` if the value
        cannot be parsed.

    Examples:
        >>> parse_category("Signal A = InLens")
        'InLens'
        >>> parse_category("Detector = SE2")
        'SE2'
        >>> parse_category(None)
        None
    """
    if not raw_string:
        return None

    match = _CATEGORY_PATTERN.search(str(raw_string))

    if not match:
        return None

    return match.group(1).strip()


def parse_value_with_unit(raw_string: object) -> tuple[float | None, str | None]:
    """
    Extract a numeric value and its unit from a SEM metadata string.

    The function expects metadata in the form
    ``"<label> = <number> <unit>"``.

    Args:
        raw_string: Raw metadata value to parse.

    Returns:
        A tuple ``(value, unit)`` if the value can be parsed.
        Returns ``(None, None)`` otherwise.

    Examples:
        >>> parse_value_with_unit("WD = 3.198 mm")
        (3.198, 'mm')
        >>> parse_value_with_unit("Pixel Size = 18.36 nm")
        (18.36, 'nm')
        >>> parse_value_with_unit("false")
        (None, None)
    """
    if not raw_string:
        return None, None

    raw_string = str(raw_string).strip()

    if raw_string.lower() == "false":
        return None, None

    match = _NUM_PATTERN.search(raw_string)

    if not match:
        return None, None

    return float(match.group(1)), match.group(2)


def _normalize_pixel_size_to_nm(
        value: float | None, 
        unit: str | None
) -> float | None:
    """
    Convert a pixel size to the canonical unit of nanometers per pixel.

    Args:
        value: Pixel size value.
        unit: Unit associated with the pixel size.

    Returns:
        Pixel size converted to nanometers per pixel, or ``None`` if
        either the value or unit is missing.
    """
    if value is None or unit is None:
        return None

    unit = unit.strip().lower()

    if unit not in _PIXEL_SIZE_UNIT_TO_NM:
        raise ValueError(f"Unknown pixel-size unit: {unit!r}")

    return float(value) * _PIXEL_SIZE_UNIT_TO_NM[unit]


def parse_pixel_size(
        raw_string: object, 
        json_field: str
) -> tuple[float | None, str | None]:
    """
    Parse and normalize a SEM pixel-size metadata value.

    Pixel sizes are converted to the canonical unit of nanometers per
    pixel (nm/pixel).

    ``COMPUTED_IMAGE_PIXEL_SIZE`` fields are expected in the form
    ``"<number> <unit>"``, while other fields are expected to use the
    standard ``"<label> = <number> <unit>"`` format.

    Args:
        raw_string: Raw pixel-size metadata value.
        json_field: Name of the JSON field containing the value.

    Returns:
        A tuple ``(value, "nm")`` containing the normalized pixel size,
        or ``(None, None)`` if the value cannot be parsed.

    Examples:
        >>> parse_pixel_size("Pixel Size = 18.36 nm", "AP_PIXEL_SIZE")
        (18.36, 'nm')
        >>> parse_pixel_size("0.0047619047619047615 µm",
        ...                  "COMPUTED_IMAGE_PIXEL_SIZE")
        (4.761904761904761, 'nm')
    """
    if not raw_string:
        return None, None

    if json_field == "COMPUTED_IMAGE_PIXEL_SIZE":
        raw_string = str(raw_string).strip()

        if raw_string.lower() == "false":
            return None, None

        match = _COMPUTED_PIXEL_SIZE_PATTERN.match(raw_string)

        if not match:
            return None, None

        value = float(match.group(1))
        unit = match.group(2)
    else:
        value, unit = parse_value_with_unit(raw_string)

    normalized_value = _normalize_pixel_size_to_nm(value, unit)

    if normalized_value is None:
        return None, None

    return normalized_value, "nm"


def parse_magnification(raw_string: object) -> tuple[float | None, str | None]:
    """
    Parse a SEM magnification value and normalize it to a numeric value.

    The function accepts magnification values in the form
    ``"Mag = <value> X"``. A ``K`` prefix is interpreted as thousands.

    Args:
        raw_string: Raw magnification metadata value.

    Returns:
        A tuple ``(magnification, "X")`` if the value can be parsed,
        or ``(None, None)`` otherwise.

    Examples:
        >>> parse_magnification("Mag = 500 X")
        (500.0, 'X')
        >>> parse_magnification("Mag = 2 K X")
        (2000.0, 'X')
        >>> parse_magnification("invalid")
        (None, None)
    """
    if raw_string is None:
        return None, None

    value = str(raw_string).strip()

    match = _MAGNIFICATION_PATTERN.search(value)

    if not match:
        return None, None

    magnitude = float(match.group(1))
    prefix = match.group(2)

    if prefix and prefix.upper() == "K":
        magnitude *= 1000

    return magnitude, "X"
