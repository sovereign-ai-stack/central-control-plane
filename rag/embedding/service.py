"""EmbeddingService facade."""

from __future__ import annotations

from collections.abc import Sequence

from rag.embedding.metrics import EmbeddingMetrics
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.protocol import EmbeddingModel
from rag.embedding.types import EmbeddingResult, ModelInfo, QueryEmbeddingResult
from rag.embedding.validation import validate_vector_store_dimension


class EmbeddingService:
    """Preprocessing + model dispatch + optional metrics."""

    def __init__(
        self,
        model: EmbeddingModel,
        preprocessor: EmbeddingPreprocessor | None = None,
        metrics: EmbeddingMetrics | None = None,
        *,
        vector_store_dimension: int | None = None,
        concurrency_limiter: object | None = None,
    ) -> None:
        self._model = model
        self._preprocessor = preprocessor or EmbeddingPreprocessor()
        self._metrics = metrics
        # Caps simultaneous embedding work. Rate limiting bounds arrivals; this
        # bounds what actually runs, which is what saturates a CPU or GPU.
        self._concurrency = concurrency_limiter
        self._validate_startup(vector_store_dimension)

    @property
    def model_info(self) -> ModelInfo:
        return self._model.info

    @property
    def model(self) -> EmbeddingModel:
        return self._model

    @property
    def preprocessor(self) -> EmbeddingPreprocessor:
        return self._preprocessor

    def embed_query(self, raw_text: str) -> QueryEmbeddingResult:
        text = self._preprocessor.preprocess(raw_text)
        with self._guard():
            result = self._model.embed_query(text)
        if self._metrics is not None:
            self._metrics.record_query(result.latency_ms)
        return result

    def embed_documents(self, raw_texts: Sequence[str]) -> EmbeddingResult:
        if not raw_texts:
            info = self._model.info
            return EmbeddingResult(vectors=[], model_info=info, latency_ms=0.0, batch_size=0)
        texts = self._preprocessor.preprocess_batch(list(raw_texts))
        with self._guard():
            result = self._model.embed_documents(texts)
        if self._metrics is not None:
            self._metrics.record_documents(result.latency_ms, result.batch_size)
        return result

    def _guard(self):
        """Concurrency cap when configured, otherwise a no-op context."""
        if self._concurrency is None:
            from contextlib import nullcontext

            return nullcontext()
        return self._concurrency

    def health_check(self) -> bool:
        return self._model.health_check()

    def _validate_startup(self, vector_store_dimension: int | None) -> None:
        if not self._model.health_check():
            raise RuntimeError("Embedding model health check failed at startup")
        if vector_store_dimension is not None:
            validate_vector_store_dimension(self._model.info, vector_store_dimension)
