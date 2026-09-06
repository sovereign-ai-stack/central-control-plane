"""
Text Normalization utilities for Semantic Routing & Intent Matching.
Handles Persian/Arabic character harmonization, half-spaces, and tokenization.
"""

import re
from typing import List, Set


def normalize_text(text: str) -> str:
    """
    Normalizes Persian and English text:
    - Harmonizes Arabic/Persian letters (ي -> ی, ك -> ک, etc.)
    - Normalizes zero-width non-joiners (half-space) to standard space for robust matching
    - Removes excessive diacritics and punctuations
    - Lowers English characters
    """
    if not text:
        return ""

    text = text.lower()

    # Persian / Arabic character unifications
    char_map = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
        "\u200c": " ",  # ZWNJ / Half-space normalized to space for phrase matching
        "\u200f": " ",
        "\u200e": " ",
        "\xa0": " ",
        "ـ": "",        # Tatweel / Kashida
    }
    for old_ch, new_ch in char_map.items():
        text = text.replace(old_ch, new_ch)

    # Remove diacritics (Aerab)
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_tokens(normalized_text: str) -> Set[str]:
    """Extracts alphanumeric word tokens from normalized text."""
    words = re.findall(r"[\w\d]+", normalized_text)
    return set(words)
