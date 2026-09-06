"""
Format-agnostic extraction result types.

`ExtractedDocument` is the boundary between format-specific extractors and the
rest of ingestion. Nothing downstream of this type knows what a PDF is: page
structure is expressed as generic `SourceSegment` records, so adding DOCX, HTML,
or Markdown later requires only a new extractor adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

SOURCE_TYPE_TEXT = "text"
SOURCE_TYPE_PDF = "pdf"

SEGMENT_LABEL_DOCUMENT = "document"
SEGMENT_LABEL_PAGE = "page"


@dataclass(frozen=True, slots=True)
class SourceSegment:
    """
    A contiguous span of the extracted text with a provenance label.

    For PDFs one segment per page (`label="page"`); for plain text a single
    segment spanning the document. Offsets are half-open `[char_start, char_end)`
    into `ExtractedDocument.text`.
    """

    label: str
    ordinal: int
    char_start: int
    char_end: int

    def contains(self, position: int) -> bool:
        return self.char_start <= position < self.char_end

    def overlaps(self, start: int, end: int) -> bool:
        return start < self.char_end and end > self.char_start


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Text plus provenance produced by a `DocumentExtractor`."""

    text: str
    source_type: str
    filename: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    segments: tuple[SourceSegment, ...] = ()
    page_count: int | None = None

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def segment_count(self) -> int:
        return len(self.segments)
