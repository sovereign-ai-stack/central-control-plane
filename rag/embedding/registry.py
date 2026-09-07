"""Model factory — no hard-coded production default."""

from __future__ import annotations

from rag.embedding.backends.heydari import HeydariPersianBackend
from rag.embedding.backends.jina_v5 import JINA_V5_MODEL_IDS, JinaEmbeddingsV5Backend
from rag.embedding.backends.sentence_transformers import SentenceTransformersBackend
from rag.embedding.config import EmbeddingConfig
from rag.embedding.errors import EmbeddingModelLoadError
from rag.embedding.protocol import EmbeddingModel
from rag.embedding.stub import StubEmbeddingModel

_HEYDARI_MODEL_ID = "heydariAI/persian-embeddings"


class ModelRegistry:
    """Factory for EmbeddingModel backends."""

    _BACKENDS = ("stub", "sentence-transformers")

    @staticmethod
    def create(config: EmbeddingConfig) -> EmbeddingModel:
        backend = config.backend
        if backend == "stub":
            return StubEmbeddingModel(
                model_id=config.model_id,
                device=config.device,
                normalization_version=config.preprocessing.normalization_version,
            )
        if backend == "sentence-transformers":
            try:
                if config.model_id == _HEYDARI_MODEL_ID or config.candidate_id == "M3-persian-heydari":
                    return HeydariPersianBackend(config)
                if config.model_id in JINA_V5_MODEL_IDS:
                    return JinaEmbeddingsV5Backend(config)
                return SentenceTransformersBackend(config)
            except Exception as exc:
                # Serving prefers a degraded answer to no answer. Measurement
                # does not: a stub silently substituted for the model under test
                # produces numbers that look real and mean nothing, so callers
                # that are measuring set strict_load and get the failure.
                if config.strict_load:
                    raise EmbeddingModelLoadError(
                        f"Strict load requested for {config.model_id}: {exc}"
                    ) from exc
                import logging
                logging.getLogger("ModelRegistry").warning(
                    f"⚠️ SentenceTransformers failed to initialize ({exc}). Falling back to ultra-fast in-process StubEmbeddingModel."
                )
                return StubEmbeddingModel(
                    dimension=384,
                    model_id=config.model_id or "stub-fallback",
                    device=config.device,
                    normalization_version=config.preprocessing.normalization_version,
                )
        raise EmbeddingModelLoadError(f"Unsupported embedding backend: {backend}")

    @staticmethod
    def list_registered_backends() -> list[str]:
        return list(ModelRegistry._BACKENDS)
