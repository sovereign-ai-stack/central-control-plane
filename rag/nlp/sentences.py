"""
Persian sentence segmentation and lightweight block structure detection.

Two jobs, both feeding adaptive chunking:

- `split_sentences` finds sentence boundaries so a chunk never cuts mid-sentence.
- `detect_blocks` labels headings, list items, and table rows so those are not
  split away from their context or merged into prose.

Structure detection is intentionally format-agnostic: it works on text alone and
knows nothing about PDFs, Markdown, or any other source format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from rag.nlp.types import Sentence

# Persian full stop is "." as well; "؟" and "!" and "؛" also terminate.
_TERMINATORS = ".؟?!؛"
_SENTENCE_END = re.compile(f"[{re.escape(_TERMINATORS)}]+[\\s]")

# Abbreviations and ordinals that must not end a sentence.
_ABBREVIATIONS = frozenset(
    {
        "ص",
        "ج",
        "ق",
        "ه",
        "ش",
        "م",
        "الخ",
        "مثلا",
        "no",
        "vol",
        "fig",
        "eq",
        "dr",
        "mr",
        "mrs",
        "prof",
    }
)

_LIST_MARKER = re.compile(
    r"^\s*(?:[-*•·–]\s+|\(?[0-9۰-۹]+[.)\-]\s+|[الفبپتثجچ][.)]\s+)"
)
_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s+\S|(?:فصل|بخش|ماده|تبصره|بند|پیوست)\s+[0-9۰-۹]+|[0-9۰-۹]+(?:\.[0-9۰-۹]+)+\s+\S)"
)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$|\t.*\t")


class BlockKind(str, Enum):
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE_ROW = "table_row"
    PARAGRAPH = "paragraph"


@dataclass(frozen=True, slots=True)
class TextBlock:
    kind: BlockKind
    text: str
    char_start: int
    char_end: int

    @property
    def is_structured(self) -> bool:
        """Structured blocks must never be split or merged into prose."""
        return self.kind is not BlockKind.PARAGRAPH


def classify_line(line: str) -> BlockKind:
    if not line.strip():
        return BlockKind.PARAGRAPH
    if _TABLE_ROW.match(line):
        return BlockKind.TABLE_ROW
    if _HEADING.match(line):
        return BlockKind.HEADING
    if _LIST_MARKER.match(line):
        return BlockKind.LIST_ITEM
    return BlockKind.PARAGRAPH


def detect_blocks(text: str) -> list[TextBlock]:
    """
    Group text into blocks, merging consecutive prose lines into paragraphs and
    keeping each heading, list item, and table row as its own block.
    """
    blocks: list[TextBlock] = []
    cursor = 0
    pending: list[str] = []
    pending_start = 0

    def flush(end: int) -> None:
        nonlocal pending, pending_start
        if pending:
            body = "\n".join(pending).strip()
            if body:
                blocks.append(
                    TextBlock(
                        kind=BlockKind.PARAGRAPH,
                        text=body,
                        char_start=pending_start,
                        char_end=end,
                    )
                )
            pending = []

    for line in text.split("\n"):
        start = cursor
        end = cursor + len(line)
        cursor = end + 1
        kind = classify_line(line)

        if not line.strip():
            flush(end)
            continue
        if kind is BlockKind.PARAGRAPH:
            if not pending:
                pending_start = start
            pending.append(line)
            continue

        flush(start)
        blocks.append(
            TextBlock(kind=kind, text=line.strip(), char_start=start, char_end=end)
        )

    flush(cursor)
    return blocks


def _is_abbreviation(text: str, terminator_index: int) -> bool:
    prefix = text[:terminator_index]
    match = re.search(r"([^\s.؟?!؛]+)$", prefix)
    if match is None:
        return False
    word = match.group(1).strip().lower()
    return word in _ABBREVIATIONS


def split_sentences(text: str) -> list[Sentence]:
    """
    Split into sentences, keeping terminators attached and guarding abbreviations.

    Newlines terminate a sentence too, so a heading or list item never merges
    into the sentence that follows it.
    """
    sentences: list[Sentence] = []
    start = 0
    position = 0
    length = len(text)

    while position < length:
        char = text[position]
        if char == "\n":
            _append(sentences, text, start, position + 1)
            position += 1
            start = position
            continue
        if char in _TERMINATORS:
            end = position + 1
            while end < length and text[end] in _TERMINATORS:
                end += 1
            if _is_abbreviation(text, position):
                position = end
                continue
            if end >= length or text[end].isspace():
                _append(sentences, text, start, end)
                position = end
                start = end
                continue
            position = end
            continue
        position += 1

    _append(sentences, text, start, length)
    return sentences


def _append(sentences: list[Sentence], text: str, start: int, end: int) -> None:
    raw = text[start:end]
    body = raw.strip()
    if not body:
        return
    offset = start + (len(raw) - len(raw.lstrip()))
    sentences.append(
        Sentence(text=body, char_start=offset, char_end=offset + len(body))
    )
