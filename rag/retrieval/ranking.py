"""Cosine similarity ranking for normalized embedding vectors."""

from __future__ import annotations

import numpy as np

from rag.embedding.types import Vector
from rag.retrieval.errors import RetrievalDimensionMismatchError


def cosine_similarity(query_vector: Vector, document_vector: Vector) -> float:
    """Dot product for L2-normalized vectors (cosine similarity)."""
    if query_vector.ndim != 1 or document_vector.ndim != 1:
        raise RetrievalDimensionMismatchError("similarity vectors must be one-dimensional")
    if query_vector.shape != document_vector.shape:
        raise RetrievalDimensionMismatchError(
            f"vector dimension mismatch: query {query_vector.shape[0]}, "
            f"document {document_vector.shape[0]}"
        )
    return float(np.dot(query_vector, document_vector))


def rank_by_similarity(
    scored_items: list[tuple[object, float, object]],
    *,
    top_k: int,
) -> list[tuple[object, float, object]]:
    """
    Sort by similarity descending, then stable tie-break on chunk_id ascending.

    Each item is (payload, score, chunk_id) where chunk_id supports comparison.
    """
    ordered = sorted(
        scored_items,
        key=lambda item: (-item[1], str(item[2])),
    )
    return ordered[:top_k]
