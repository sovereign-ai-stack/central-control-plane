"""EmbeddingModel protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from rag.embedding.types import EmbeddingResult, ModelInfo, QueryEmbeddingResult


class EmbeddingModel(Protocol):
    """Replaceable local embedding backend."""

    @property
    def info(self) -> ModelInfo:
        """Model metadata; dimension discovered at load time for real backends."""
        ...

    def embed_query(self, text: str) -> QueryEmbeddingResult:
        """Embed a single preprocessed query string."""
        ...

    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        """Embed a batch of preprocessed document strings."""
        ...

    def health_check(self) -> bool:
        """Return True if model loaded and probe embedding succeeds."""
        ...
