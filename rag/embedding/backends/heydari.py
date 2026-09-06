"""Heydari Persian embedding backend — benchmark candidate only."""

from __future__ import annotations

from rag.embedding.backends.sentence_transformers import SentenceTransformersBackend
from rag.embedding.config import EmbeddingConfig
from rag.embedding.errors import EmbeddingModelLoadError

_HEYDARI_MODEL_ID = "heydariAI/persian-embeddings"


class HeydariPersianBackend(SentenceTransformersBackend):
    """
    Local adapter for heydariAI/persian-embeddings.

    Not production — dimension is discovered at runtime from the loaded model.
    Model identifier remains in configuration/adapter layer only.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        if config.model_id != _HEYDARI_MODEL_ID:
            raise EmbeddingModelLoadError(
                "HeydariPersianBackend requires the configured heydari Persian model id"
            )
        normalized = EmbeddingConfig(
            backend=config.backend,
            model_id=_HEYDARI_MODEL_ID,
            revision=config.revision,
            device=config.device,
            batch_size=config.batch_size,
            normalize_embeddings=config.normalize_embeddings,
            query_prefix=None,
            document_prefix=None,
            torch_seed=config.torch_seed,
            max_sequence_length=config.max_sequence_length,
            preprocessing=config.preprocessing,
            candidate_id=config.candidate_id or "M3-persian-heydari",
            production=False,
        )
        super().__init__(normalized)
