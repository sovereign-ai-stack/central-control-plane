"""Request validation and content hashing."""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from rag.ingestion.errors import IngestContentTooLargeError, IngestValidationError
from rag.ingestion.types import IngestDocumentRequest, IngestDocumentUpdateRequest

MAX_CONTENT_BYTES = 1_048_576  # 1 MB per spec assumption
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def content_hash(normalized_content: str) -> str:
    return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()


def chunk_content_hash(normalized_chunk: str) -> str:
    return hashlib.sha256(normalized_chunk.encode("utf-8")).hexdigest()


def validate_create_request(request: IngestDocumentRequest) -> None:
    if request.content is None:
        raise IngestValidationError("content is required")
    if not request.content.strip():
        raise IngestValidationError("content must not be empty or whitespace-only")
    if not request.source or not request.source.strip():
        raise IngestValidationError("source is required")
    _validate_scope_ids(request.company_id, request.department_id)
    _validate_content_size(request.content)


def validate_update_request(request: IngestDocumentUpdateRequest) -> None:
    if not request.content.strip():
        raise IngestValidationError("content must not be empty or whitespace-only")
    _validate_scope_ids(request.company_id, request.department_id)
    _validate_content_size(request.content)


def _validate_scope_ids(company_id: UUID, department_id: UUID) -> None:
    if company_id is None or department_id is None:
        raise IngestValidationError("company_id and department_id are required")


def _validate_content_size(content: str) -> None:
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise IngestContentTooLargeError("content exceeds maximum allowed size")
