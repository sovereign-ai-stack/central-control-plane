"""
Deterministic candidate ordering (spec 005-rag-pipeline/interface.md §4).

Sort keys are total orders over server-side metadata only, so the same input
always produces the same output regardless of dict/set iteration order.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from rag.contracts.retrieval import RetrievedChunk


def retrieval_sort_key(chunk: RetrievedChunk) -> tuple[float, str, int, str]:
    """Retrieval score descending, then document_id, chunk_index, chunk_id ascending."""
    return (
        -chunk.score,
        str(chunk.document_id),
        chunk.chunk_index,
        str(chunk.chunk_id),
    )


def final_sort_key(
    chunk: RetrievedChunk,
    rerank_scores: Mapping[UUID, float],
) -> tuple[float, float, str, int, str]:
    """
    Rerank score descending (retrieval score when the chunk has no rerank score),
    then retrieval score descending, then document_id, chunk_index, chunk_id.
    """
    rerank_score = rerank_scores.get(chunk.chunk_id)
    primary = chunk.score if rerank_score is None else rerank_score
    return (
        -primary,
        -chunk.score,
        str(chunk.document_id),
        chunk.chunk_index,
        str(chunk.chunk_id),
    )


def order_by_retrieval(
    candidates: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    return sorted(candidates, key=retrieval_sort_key)


def order_final(
    candidates: list[RetrievedChunk],
    rerank_scores: Mapping[UUID, float],
) -> list[RetrievedChunk]:
    return sorted(candidates, key=lambda chunk: final_sort_key(chunk, rerank_scores))
