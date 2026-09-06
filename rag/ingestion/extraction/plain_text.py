"""Plain-text extractor — the default adapter."""

from __future__ import annotations

from rag.ingestion.extraction.errors import CorruptDocumentError, EmptyDocumentError
from rag.ingestion.extraction.limits import Deadline, ExtractionLimits
from rag.ingestion.extraction.types import (
    SEGMENT_LABEL_DOCUMENT,
    SOURCE_TYPE_TEXT,
    ExtractedDocument,
    SourceSegment,
)

_BOM = "﻿"


class PlainTextExtractor:
    """
    Decodes UTF-8 (or UTF-8 with BOM) text into a single-segment document.

    A single segment spanning the whole document keeps the position model
    uniform: downstream code resolves chunk offsets to segments identically for
    text and PDF.
    """

    def __init__(self, limits: ExtractionLimits | None = None) -> None:
        self._limits = limits or ExtractionLimits()

    @property
    def source_type(self) -> str:
        return SOURCE_TYPE_TEXT

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".txt", ".text", ".md", ".markdown")

    def sniff(self, data: bytes) -> bool:
        """Plain text is the fallback: accept anything that decodes as UTF-8."""
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True

    def extract(
        self,
        data: bytes,
        *,
        filename: str | None = None,
        deadline: Deadline | None = None,
    ) -> ExtractedDocument:
        _ = deadline  # decoding is a single bounded operation
        self._limits.check_file_size(len(data))
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CorruptDocumentError("file is not valid UTF-8 text") from exc

        text = text.removeprefix(_BOM)
        self._limits.check_extracted_chars(len(text))

        if not text.strip():
            raise EmptyDocumentError("file contains no extractable text")

        return ExtractedDocument(
            text=text,
            source_type=SOURCE_TYPE_TEXT,
            filename=filename,
            metadata={},
            segments=(
                SourceSegment(
                    label=SEGMENT_LABEL_DOCUMENT,
                    ordinal=1,
                    char_start=0,
                    char_end=len(text),
                ),
            ),
            page_count=None,
        )


def extract_from_string(text: str, *, filename: str | None = None) -> ExtractedDocument:
    """Wrap an already-decoded string, for callers that never touch bytes."""
    return PlainTextExtractor().extract(text.encode("utf-8"), filename=filename)
