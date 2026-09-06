"""Attach document embeddings to stored chunks during ingestion."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import numpy as np

from rag.embedding.errors import EmbeddingError
from rag.embedding.service import EmbeddingService
from rag.embedding.types import Vector
from rag.ingestion.errors import IngestEmbeddingError
from rag.ingestion.types import StoredChunk


def embed_and_attach_chunks(
    embedding_service: EmbeddingService,
    chunks: Sequence[StoredChunk],
) -> list[StoredChunk]:
    """Batch-embed chunk texts and attach vectors in input order."""
    if not chunks:
        return []

    # Embed the processed representation when the NLP layer produced one; the
    # stored `content` stays the normalized text that retrieval returns.
    texts = [chunk.text_for_embedding for chunk in chunks]
    try:
        result = embedding_service.embed_documents(texts)
    except EmbeddingError as exc:
        raise IngestEmbeddingError("document embedding failed") from exc

    if len(result.vectors) != len(chunks):
        raise IngestEmbeddingError(
            f"embedding count mismatch: expected {len(chunks)}, got {len(result.vectors)}"
        )

    model_info = result.model_info
    attached: list[StoredChunk] = []
    for chunk, vector in zip(chunks, result.vectors, strict=True):
        _validate_chunk_vector(vector, model_info.dimension, model_info.model_id)
        attached.append(
            replace(
                chunk,
                embedding=vector,
                embedding_model_id=model_info.model_id,
                embedding_dimension=model_info.dimension,
            )
        )
    return attached


def _validate_chunk_vector(vector: Vector, expected_dimension: int, model_id: str) -> None:
    if vector.ndim != 1:
        raise IngestEmbeddingError(
            f"embedding for model {model_id} must be one-dimensional"
        )
    if vector.shape[0] != expected_dimension:
        raise IngestEmbeddingError(
            f"embedding dimension mismatch for model {model_id}: "
            f"expected {expected_dimension}, got {vector.shape[0]}"
        )
    if vector.dtype != np.float32:
        raise IngestEmbeddingError(
            f"embedding for model {model_id} must be float32, got {vector.dtype}"
        )
