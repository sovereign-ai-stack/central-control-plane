"""Scope-aware vector search over persisted chunk embeddings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from rag.embedding.types import Vector
from rag.ingestion.types import StoredChunk
from rag.retrieval.errors import RetrievalDimensionMismatchError, RetrievalModelMismatchError
from rag.retrieval.ranking import cosine_similarity, rank_by_similarity

SEARCHABLE_DOCUMENT_STATUS = "indexed"


@dataclass(frozen=True, slots=True)
class VectorSearchScope:
    """
    The authorized search scope. Built from `AuthorizationContext` only.

    `allowed_document_ids=None` means "every INDEXED document in scope",
    resolved by the store from each chunk's denormalised `document_status`.
    That removes the per-query scan of every document. Passing an explicit set
    still narrows further, exactly as before.
    """

    company_id: UUID
    allowed_department_ids: tuple[UUID, ...]
    allowed_document_ids: frozenset[UUID] | None = None


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: StoredChunk
    score: float


@runtime_checkable
class VectorStore(Protocol):
    def search(
        self,
        query_vector: Vector,
        scope: VectorSearchScope,
        *,
        top_k: int,
        query_model_id: str,
        query_dimension: int,
    ) -> tuple[list[ScoredChunk], int]:
        ...


def search_scoped_chunks(
    chunks: Sequence[StoredChunk],
    query_vector: Vector,
    scope: VectorSearchScope,
    *,
    top_k: int,
    query_model_id: str,
    query_dimension: int,
) -> tuple[list[ScoredChunk], int]:
    """Linear scan over in-memory chunks with mandatory scope filtering."""
    if query_vector.ndim != 1 or query_vector.shape[0] != query_dimension:
        raise RetrievalDimensionMismatchError(
            f"query vector dimension {query_vector.shape} "
            f"does not match expected {query_dimension}"
        )

    allowed_departments = set(scope.allowed_department_ids)
    scored: list[tuple[StoredChunk, float, UUID]] = []

    for chunk in chunks:
        if chunk.company_id != scope.company_id:
            continue
        if chunk.department_id not in allowed_departments:
            continue
        if (
            scope.allowed_document_ids is not None
            and chunk.document_id not in scope.allowed_document_ids
        ):
            continue
        if (
            scope.allowed_document_ids is None
            and chunk.document_status != SEARCHABLE_DOCUMENT_STATUS
        ):
            # Fail closed: a chunk with no recorded status is not searchable.
            continue
        if chunk.embedding is None or chunk.embedding_model_id is None:
            continue
        if chunk.embedding_model_id != query_model_id:
            raise RetrievalModelMismatchError(
                f"stored chunk model {chunk.embedding_model_id!r} "
                f"does not match query model {query_model_id!r}"
            )
        if chunk.embedding_dimension != query_dimension:
            raise RetrievalDimensionMismatchError(
                f"stored chunk dimension {chunk.embedding_dimension} "
                f"does not match query dimension {query_dimension}"
            )
        score = cosine_similarity(query_vector, chunk.embedding)
        scored.append((chunk, score, chunk.chunk_id))

    ranked = rank_by_similarity(scored, top_k=top_k)
    results = [ScoredChunk(chunk=item[0], score=item[1]) for item in ranked]
    return results, len(scored)
