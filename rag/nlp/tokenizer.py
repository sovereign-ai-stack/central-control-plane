"""
Persian word tokenization.

ZWNJ is treated as *inside* a token, not as a separator: `کتاب‌ها` is one token
whose plural suffix morphology can then strip. This is the property fa-norm-v1
cannot provide, since it rewrites ZWNJ to a space before tokenization ever runs.
"""

from __future__ import annotations

import re

from rag.nlp.normalizer import ZWNJ

_WORD_CHARS = f"0-9A-Za-z_ء-ي٠-٩ٮ-ۓ۰-۹{ZWNJ}"
_WORD = re.compile(f"[{_WORD_CHARS}]+")


def tokenize(text: str) -> list[str]:
    """Split into word tokens, keeping ZWNJ-joined compounds intact."""
    return [match.group() for match in _WORD.finditer(text)]


def tokenize_with_spans(text: str) -> list[tuple[str, int, int]]:
    """Tokens with their `[start, end)` offsets into `text`."""
    return [(m.group(), m.start(), m.end()) for m in _WORD.finditer(text)]


def count_tokens(text: str) -> int:
    """Word-token count — the unit adaptive chunking sizes chunks in."""
    return sum(1 for _ in _WORD.finditer(text))
