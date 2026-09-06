"""Input hashing and dimension validation utilities."""

from __future__ import annotations

import hashlib

from rag.embedding.errors import EmbeddingDimensionMismatch
from rag.embedding.types import ModelInfo


def hash_input_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_vector_store_dimension(model_info: ModelInfo, expected_dimension: int) -> None:
    if model_info.dimension != expected_dimension:
        raise EmbeddingDimensionMismatch(
            f"Model dimension {model_info.dimension} does not match "
            f"configured vector store dimension {expected_dimension}"
        )
