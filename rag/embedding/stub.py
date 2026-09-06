"""Deterministic stub embeddings for CI and tests."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence

import numpy as np

from rag.embedding.types import EmbeddingResult, ModelInfo, QueryEmbeddingResult, Vector


class StubEmbeddingModel:
    """Deterministic fake embeddings — no external dependencies."""

    def __init__(
        self,
        dimension: int = 384,
        model_id: str = "stub-v1",
        normalization_version: str = "fa-norm-v1",
        device: str = "cpu",
    ) -> None:
        self._dimension = dimension
        self._model_id = model_id
        self._normalization_version = normalization_version
        self._device = device

    @property
    def info(self) -> ModelInfo:
        return ModelInfo(
            model_id=self._model_id,
            revision=None,
            dimension=self._dimension,
            max_sequence_length=512,
            normalization_version=self._normalization_version,
            query_prefix=None,
            document_prefix=None,
            device=self._device,
            backend="stub",
            normalize_embeddings=True,
        )

    def embed_query(self, text: str) -> QueryEmbeddingResult:
        started = time.perf_counter()
        vector = self._vector_for_text(text)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return QueryEmbeddingResult(
            vector=vector,
            model_info=self.info,
            latency_ms=elapsed_ms,
        )

    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        started = time.perf_counter()
        vectors = [self._vector_for_text(text) for text in texts]
        elapsed_ms = (time.perf_counter() - started) * 1000
        return EmbeddingResult(
            vectors=vectors,
            model_info=self.info,
            latency_ms=elapsed_ms,
            batch_size=len(texts),
        )

    def health_check(self) -> bool:
        result = self.embed_query("probe")
        return result.vector.shape == (self._dimension,)

    def _vector_for_text(self, text: str) -> Vector:
        digest = hashlib.sha256(f"{self._model_id}:{text}".encode()).hexdigest()
        seed = int(digest[:16], 16)
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(self._dimension).astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector
