"""
Preprocessing before embedding.

This is the **single symmetric hook** for the Persian NLP layer. `EmbeddingService`
already routes both `embed_query` and `embed_documents` through here, so
attaching the pipeline at this point applies the identical transform to queries
and documents without touching `SecureRetrievalEngine`, `RetrievalService`, or
the Phase 4 reranking pipeline. Asymmetry here would put queries and documents in
different spaces and destroy recall.

With no pipeline attached the behaviour is exactly fa-norm-v1, as before Phase 5.
"""

from __future__ import annotations

from rag.embedding.errors import EmbeddingValidationError
from rag.ingestion.persian import normalization_version, normalize_persian
from rag.nlp.normalizer import NORMALIZATION_VERSION_V2
from rag.nlp.pipeline import PersianNlpPipeline


class EmbeddingPreprocessor:
    """Applies fa-norm-v1, or the Persian NLP pipeline when one is attached."""

    def __init__(
        self,
        normalization_version_name: str = "fa-norm-v1",
        *,
        nlp: PersianNlpPipeline | None = None,
    ) -> None:
        self._nlp = nlp if (nlp is not None and nlp.config.enabled) else None
        supported = {normalization_version()}
        if self._nlp is not None:
            supported.add(NORMALIZATION_VERSION_V2)
        if normalization_version_name not in supported:
            raise EmbeddingValidationError(
                f"Unsupported normalization version: {normalization_version_name}"
            )
        self._normalization_version = (
            self._nlp.config.normalization_version
            if self._nlp is not None
            else normalization_version_name
        )

    @property
    def normalization_version(self) -> str:
        return self._normalization_version

    @property
    def nlp(self) -> PersianNlpPipeline | None:
        return self._nlp

    @property
    def nlp_enabled(self) -> bool:
        return self._nlp is not None

    def preprocess(self, raw_text: str) -> str:
        if raw_text is None:
            raise EmbeddingValidationError("text is required")
        normalized = (
            self._nlp.embedding_text(raw_text)
            if self._nlp is not None
            else normalize_persian(raw_text)
        )
        if not normalized.strip():
            raise EmbeddingValidationError("text must not be empty after preprocessing")
        return normalized

    def preprocess_batch(self, raw_texts: list[str]) -> list[str]:
        return [self.preprocess(text) for text in raw_texts]
