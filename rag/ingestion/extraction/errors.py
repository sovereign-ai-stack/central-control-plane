"""
Document extraction errors.

Messages are deliberately generic: they never echo file paths, raw bytes, or
parser internals, because extraction runs on caller-supplied files. Every error
carries an explicit non-5xx status so a malformed upload is reported as a client
error rather than surfacing as an internal failure.
"""

from __future__ import annotations

from rag.ingestion.errors import IngestError


class ExtractionError(IngestError):
    """Base document extraction error."""

    code = "INGEST_EXTRACTION_FAILED"
    http_status = 400


class UnsupportedSourceTypeError(ExtractionError):
    """No registered extractor handles the requested source type."""

    code = "INGEST_UNSUPPORTED_SOURCE_TYPE"
    http_status = 415


class CorruptDocumentError(ExtractionError):
    """File is malformed, encrypted, or otherwise unreadable."""

    code = "INGEST_CORRUPT_DOCUMENT"
    http_status = 400


class EmptyDocumentError(ExtractionError):
    """File parsed successfully but yielded no extractable text."""

    code = "INGEST_EMPTY_DOCUMENT"
    http_status = 400


class ExtractionLimitError(ExtractionError):
    """File exceeds a configured extraction limit (size, pages, or characters)."""

    code = "INGEST_EXTRACTION_LIMIT"
    http_status = 413


class ExtractionTimeoutError(ExtractionLimitError):
    """
    Extraction exceeded its time budget.

    A resource limit expressed in time rather than bytes, so it shares the 413
    semantics of the other limits: the document costs more than the service is
    willing to spend on it.
    """

    code = "INGEST_EXTRACTION_TIMEOUT"
