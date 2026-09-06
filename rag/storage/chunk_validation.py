"""
Write-time validation shared by every `ChunkStore` backend.

Extracted so the in-memory and Weaviate stores cannot drift apart: both enforce
the same preconditions before anything is persisted. For a backend without
transactions this is also the first line of atomicity — most failure modes are
rejected before a single object is written.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from rag.ingestion.types import StoredChunk


def validate_chunk(chunk: StoredChunk) -> None:
    """Security metadata and embedding preconditions for one chunk."""
    if not all(
        [chunk.chunk_id, chunk.document_id, chunk.company_id, chunk.department_id]
    ):
        raise ValueError("chunk missing security metadata")
    if (
        chunk.embedding is None
        or chunk.embedding_model_id is None
        or chunk.embedding_dimension is None
    ):
        raise ValueError("chunk missing embedding metadata")
    if chunk.embedding.ndim != 1:
        raise ValueError("chunk embedding must be one-dimensional")
    if chunk.embedding.shape[0] != chunk.embedding_dimension:
        raise ValueError("chunk embedding dimension mismatch")
    if chunk.embedding.dtype.name != "float32":
        raise ValueError("chunk embedding must be float32")


def validate_chunk_batch(
    document_id: UUID,
    chunks: Sequence[StoredChunk],
) -> None:
    """
    Validate a whole document batch.

    A batch must belong to one document and carry a single company/department
    scope; a mixed-scope batch would let one write span two tenants.
    """
    for chunk in chunks:
        if chunk.document_id != document_id:
            raise ValueError("chunk document_id mismatch")
        validate_chunk(chunk)

    if not chunks:
        return

    expected_company = chunks[0].company_id
    expected_department = chunks[0].department_id
    for chunk in chunks:
        if (
            chunk.company_id != expected_company
            or chunk.department_id != expected_department
        ):
            raise ValueError("chunk security scope mismatch within batch")
