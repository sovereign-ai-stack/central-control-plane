"""Ingestion pipeline errors."""

from __future__ import annotations


class IngestError(Exception):
    """Base ingestion error."""

    code: str = "INGEST_ERROR"
    http_status: int = 500


class IngestValidationError(IngestError):
    code = "INGEST_VALIDATION_ERROR"
    http_status = 400


class IngestAuthzDeniedError(IngestError):
    code = "INGEST_AUTHZ_DENIED"
    http_status = 403


class IngestUnauthorizedError(IngestError):
    code = "INGEST_UNAUTHORIZED"
    http_status = 401


class IngestDuplicateError(IngestError):
    code = "INGEST_DUPLICATE"
    http_status = 409


class IngestNotFoundError(IngestError):
    code = "INGEST_NOT_FOUND"
    http_status = 404


class IngestPipelineError(IngestError):
    code = "INGEST_PIPELINE_FAILED"
    http_status = 503


class IngestEmbeddingError(IngestPipelineError):
    code = "INGEST_EMBEDDING_FAILED"


class IngestContentTooLargeError(IngestError):
    code = "INGEST_CONTENT_TOO_LARGE"
    http_status = 413


def ingest_error_http_status(error: IngestError) -> int:
    return error.http_status
