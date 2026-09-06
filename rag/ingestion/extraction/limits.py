"""
Extraction resource limits.

Limits are checked *before* and *during* parsing so a hostile or accidentally
huge upload cannot exhaust memory or CPU. They are enforced after authorization,
never before it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from rag.ingestion.extraction.errors import (
    ExtractionLimitError,
    ExtractionTimeoutError,
)

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PAGES = 2_000
MAX_EXTRACTED_CHARS = 5_000_000
# Wall-clock budget for parsing one document. A hostile PDF can burn
# unbounded CPU inside the parser; size and page caps do not bound time.
EXTRACTION_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class ExtractionLimits:
    max_file_bytes: int = MAX_FILE_BYTES
    max_pages: int = MAX_PAGES
    max_extracted_chars: int = MAX_EXTRACTED_CHARS
    timeout_seconds: float = EXTRACTION_TIMEOUT_SECONDS

    def check_file_size(self, size_bytes: int) -> None:
        if size_bytes > self.max_file_bytes:
            raise ExtractionLimitError(
                f"file exceeds maximum size of {self.max_file_bytes} bytes"
            )

    def check_page_count(self, pages: int) -> None:
        if pages > self.max_pages:
            raise ExtractionLimitError(
                f"document exceeds maximum of {self.max_pages} pages"
            )

    def check_extracted_chars(self, chars: int) -> None:
        if chars > self.max_extracted_chars:
            raise ExtractionLimitError(
                f"extracted text exceeds maximum of {self.max_extracted_chars} characters"
            )


class Deadline:
    """
    A monotonic wall-clock budget for one extraction.

    Checked cooperatively between pages so a slow document stops *doing work*
    rather than merely being abandoned. The hard outer timeout in
    `run_with_timeout` covers the case where a single operation hangs.
    """

    __slots__ = ("_deadline", "_seconds")

    def __init__(self, seconds: float) -> None:
        self._seconds = seconds
        self._deadline = time.monotonic() + seconds if seconds > 0 else None

    @property
    def seconds(self) -> float:
        return self._seconds

    @property
    def expired(self) -> bool:
        return self._deadline is not None and time.monotonic() > self._deadline

    def check(self) -> None:
        if self.expired:
            raise ExtractionTimeoutError(
                f"document extraction exceeded {self._seconds:g} seconds"
            )


def unlimited_deadline() -> Deadline:
    """A deadline that never expires, for callers that manage their own budget."""
    return Deadline(0.0)
