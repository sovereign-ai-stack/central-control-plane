"""
The `DocumentExtractor` contract.

Extractors are the only place in the codebase allowed to know about a specific
file format. They convert bytes into an `ExtractedDocument` and nothing else:
no normalization, no chunking, no embedding, no authorization.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag.ingestion.extraction.limits import Deadline
from rag.ingestion.extraction.types import ExtractedDocument


@runtime_checkable
class DocumentExtractor(Protocol):
    """Converts raw file bytes of one format into text plus provenance."""

    @property
    def source_type(self) -> str:
        """Canonical source type this extractor produces, e.g. "pdf"."""
        ...

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        """Lowercase filename suffixes including the dot, e.g. (".pdf",)."""
        ...

    def sniff(self, data: bytes) -> bool:
        """True when the leading bytes look like this extractor's format."""
        ...

    def extract(
        self,
        data: bytes,
        *,
        filename: str | None = None,
        deadline: Deadline | None = None,
    ) -> ExtractedDocument:
        """
        Parse `data` into an `ExtractedDocument`.

        Implementations should check `deadline` between units of work so a slow
        document stops rather than running to completion.

        Raises:
            CorruptDocumentError: file is malformed or encrypted
            EmptyDocumentError: no extractable text
            ExtractionLimitError: file exceeds a configured limit
            ExtractionTimeoutError: extraction exceeded its time budget
        """
        ...
