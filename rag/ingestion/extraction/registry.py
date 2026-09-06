"""
Extractor selection.

Adding a format means registering one more adapter here; no other layer changes.
Selection order is deliberate and deterministic:

1. explicitly declared `source_type` (caller states the format)
2. content sniffing (magic bytes — trusted over the filename)
3. filename extension (a hint only, since callers control filenames)

Content is trusted over filename so a `.txt`-named PDF is still parsed as a PDF
rather than yielding mojibake.
"""

from __future__ import annotations

import inspect
from pathlib import PurePosixPath

from rag.ingestion.extraction.errors import UnsupportedSourceTypeError
from rag.ingestion.extraction.limits import Deadline, ExtractionLimits
from rag.ingestion.extraction.pdf import PdfExtractor
from rag.ingestion.extraction.plain_text import PlainTextExtractor
from rag.ingestion.extraction.protocol import DocumentExtractor
from rag.ingestion.extraction.timeout import run_with_timeout
from rag.ingestion.extraction.types import ExtractedDocument


class ExtractorRegistry:
    """Chooses the extractor for a file and delegates extraction to it."""

    def __init__(
        self,
        extractors: list[DocumentExtractor] | None = None,
        limits: ExtractionLimits | None = None,
    ) -> None:
        self._limits = limits or ExtractionLimits()
        self._extractors: list[DocumentExtractor] = list(
            extractors if extractors is not None else default_extractors(self._limits)
        )
        self._accepts_deadline: dict[int, bool] = {}

    @property
    def source_types(self) -> tuple[str, ...]:
        return tuple(extractor.source_type for extractor in self._extractors)

    def register(self, extractor: DocumentExtractor) -> None:
        """Add an adapter for a new format (DOCX, HTML, Markdown, ...)."""
        self._extractors.append(extractor)

    def for_source_type(self, source_type: str) -> DocumentExtractor:
        for extractor in self._extractors:
            if extractor.source_type == source_type:
                return extractor
        raise UnsupportedSourceTypeError(f"unsupported source type: {source_type!r}")

    def select(
        self,
        data: bytes,
        *,
        filename: str | None = None,
        source_type: str | None = None,
    ) -> DocumentExtractor:
        if source_type is not None:
            return self.for_source_type(source_type)

        for extractor in self._extractors:
            if extractor.source_type != "text" and extractor.sniff(data):
                return extractor

        suffix = _suffix(filename)
        if suffix:
            for extractor in self._extractors:
                if suffix in extractor.supported_extensions:
                    return extractor

        for extractor in self._extractors:
            if extractor.source_type == "text" and extractor.sniff(data):
                return extractor

        raise UnsupportedSourceTypeError(
            "no registered extractor can handle this document"
        )

    @property
    def limits(self) -> ExtractionLimits:
        return self._limits

    def extract(
        self,
        data: bytes,
        *,
        filename: str | None = None,
        source_type: str | None = None,
    ) -> ExtractedDocument:
        """
        Select an adapter and parse, under a wall-clock budget.

        The timeout wraps every format, not just PDF, so a future adapter
        inherits the protection instead of having to remember it.
        """
        extractor = self.select(data, filename=filename, source_type=source_type)
        timeout = self._limits.timeout_seconds
        deadline = Deadline(timeout)

        def parse() -> ExtractedDocument:
            # `deadline` is optional in the adapter signature: an adapter
            # written before it existed still works, and still gets the hard
            # timeout below. It only forgoes cooperative cancellation.
            if self._supports_deadline(extractor):
                return extractor.extract(
                    data, filename=filename, deadline=deadline
                )
            return extractor.extract(data, filename=filename)

        return run_with_timeout(parse, timeout)

    def _supports_deadline(self, extractor: DocumentExtractor) -> bool:
        key = id(extractor)
        cached = self._accepts_deadline.get(key)
        if cached is None:
            try:
                parameters = inspect.signature(extractor.extract).parameters
                cached = "deadline" in parameters
            except (TypeError, ValueError):
                cached = False
            self._accepts_deadline[key] = cached
        return cached


def default_extractors(
    limits: ExtractionLimits | None = None,
) -> list[DocumentExtractor]:
    shared = limits or ExtractionLimits()
    return [PdfExtractor(shared), PlainTextExtractor(shared)]


def _suffix(filename: str | None) -> str | None:
    if not filename:
        return None
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    return suffix or None
