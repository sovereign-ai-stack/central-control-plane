"""Persian text normalization — fa-norm-v1."""

from __future__ import annotations

import re
import unicodedata

from rag.ingestion.types import NORMALIZATION_VERSION

_ARABIC_YEH = "\u064a"
_PERSIAN_YEH = "\u06cc"
_ARABIC_KAF = "\u0643"
_PERSIAN_KAF = "\u06a9"
_ZWNJ = "\u200c"
_ZWJ = "\u200d"
_NBSP = "\u00a0"
_THIN_SPACE = "\u2009"
_ZERO_WIDTH = "\u200b"
_BOM = "\ufeff"

_CHAR_MAP = str.maketrans(
    {
        _ARABIC_YEH: _PERSIAN_YEH,
        _ARABIC_KAF: _PERSIAN_KAF,
        "\u0626": _PERSIAN_YEH,  # yeh with hamza
        "\u0624": "\u0648",  # waw with hamza
        _NBSP: " ",
        _THIN_SPACE: " ",
        _ZERO_WIDTH: "",
        _BOM: "",
    }
)


def normalize_persian(text: str) -> str:
    """Apply fa-norm-v1 normalization pipeline."""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.translate(_CHAR_MAP)
    normalized = normalized.replace(_ZWNJ, " ").replace(_ZWJ, " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.strip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def normalization_version() -> str:
    return NORMALIZATION_VERSION
