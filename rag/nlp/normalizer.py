"""
Persian normalization — fa-norm-v2.

This is an **additive** version. `rag.ingestion.persian.normalize_persian`
(fa-norm-v1) is left byte-for-byte unchanged because its output feeds stored
document content hashes, chunk dedup keys, the retrieval lexical scorer, and the
Phase 4 query hash; changing it would invalidate persisted data.

What v2 adds over v1:

- ZWNJ is **canonicalized, not deleted**. v1 maps ZWNJ to a space, which turns
  `کتاب‌ها` into two tokens and destroys the compound structure morphology needs.
  v2 keeps a single ZWNJ between letters so suffixes stay attachable.
- Diacritic (harakat) and tatweel removal.
- Punctuation canonicalization (Arabic/Latin variants folded to one form).
- Optional digit folding (Persian/Arabic-Indic to ASCII).

v2 is idempotent: `normalize(normalize(x)) == normalize(x)`.
"""

from __future__ import annotations

import re
import unicodedata

NORMALIZATION_VERSION_V2 = "fa-norm-v2"

ZWNJ = "‌"
_ZWJ = "‍"

# Arabic presentation and lookalike characters folded to their Persian forms.
_CHAR_MAP = str.maketrans(
    {
        "ي": "ی",  # arabic yeh -> persian yeh
        "ى": "ی",  # alef maksura -> persian yeh
        "ئ": "ی",  # yeh with hamza -> persian yeh
        "ك": "ک",  # arabic kaf -> persian kaf
        "ڪ": "ک",  # swash kaf -> persian kaf
        "ؤ": "و",  # waw with hamza -> waw
        "إ": "ا",  # alef with hamza below -> alef
        "أ": "ا",  # alef with hamza above -> alef
        "ة": "ه",  # teh marbuta -> heh
        "ۀ": "ه",  # heh with yeh above -> heh
        "ـ": "",  # tatweel
        " ": " ",  # no-break space
        " ": " ",  # thin space
        "\u200b": "",  # zero-width space
        "﻿": "",  # byte order mark
        "،": "،",  # arabic comma (kept, listed for clarity)
        "٫": ".",  # arabic decimal separator
        "٬": ",",  # arabic thousands separator
        "«": '"',
        "»": '"',
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
    }
)

# Harakat / tashkil.
_DIACRITICS = re.compile(r"[ً-ْٓ-ٰٕ]")

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_PERSIAN_LETTER = r"ء-يٱ-ۓیکگپچژ"

_MULTI_ZWNJ = re.compile(f"{ZWNJ}{{2,}}")
# ZWNJ only carries meaning between two letters; anywhere else it is noise.
_ZWNJ_AROUND_SPACE = re.compile(f"[ \t]*{ZWNJ}[ \t]*(?=[^{_PERSIAN_LETTER}])|(?<=[^{_PERSIAN_LETTER}])[ \t]*{ZWNJ}[ \t]*")
_ZWNJ_EDGE = re.compile(f"(?:^|(?<=\\s)){ZWNJ}|{ZWNJ}(?=\\s|$)")

_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_persian_v2(text: str, *, fold_digits: bool = False) -> str:
    """Apply fa-norm-v2. Idempotent."""
    if not text:
        return ""

    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.translate(_CHAR_MAP)
    normalized = _DIACRITICS.sub("", normalized)
    normalized = normalized.replace(_ZWJ, "")

    if fold_digits:
        normalized = normalized.translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)

    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _MULTI_ZWNJ.sub(ZWNJ, normalized)
    normalized = _ZWNJ_AROUND_SPACE.sub(" ", normalized)
    normalized = _ZWNJ_EDGE.sub("", normalized)
    normalized = _SPACES.sub(" ", normalized)
    normalized = _BLANK_LINES.sub("\n\n", normalized)

    lines = [line.strip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def strip_zwnj(text: str) -> str:
    """Drop ZWNJ entirely — used when comparing spaced and joined spellings."""
    return text.replace(ZWNJ, "")


def zwnj_to_space(text: str) -> str:
    """fa-norm-v1 compatible ZWNJ handling, for cross-version comparisons."""
    return text.replace(ZWNJ, " ")


def normalization_version_v2() -> str:
    return NORMALIZATION_VERSION_V2
