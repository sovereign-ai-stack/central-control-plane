"""Local backend integration tests — optional heavy dependencies."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rag.embedding.backends.heydari import HeydariPersianBackend
from rag.embedding.config import load_candidate_config
from rag.embedding.errors import EmbeddingDeviceError, EmbeddingModelLoadError
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService

REPO_ROOT = Path(__file__).resolve().parents[4]
CANDIDATES_PATH = REPO_ROOT / "benchmarks" / "persian" / "config" / "candidates.yaml"

pytest.importorskip("sentence_transformers")
pytest.importorskip("torch")


@pytest.mark.bench
class TestLocalEmbeddingBackends:
    @pytest.fixture
    def service_factory(self):
        def _make(candidate_id: str) -> EmbeddingService:
            config = load_candidate_config(candidate_id, CANDIDATES_PATH, device="cpu")
            model = ModelRegistry.create(config)
            return EmbeddingService(model, EmbeddingPreprocessor())

        return _make

    @pytest.mark.parametrize(
        "candidate_id",
        ["M0-baseline", "M1-e5-large", "M2-bge-m3", "M3-persian-heydari"],
    )
    def test_candidate_load_and_probe(self, service_factory, candidate_id: str):
        service = service_factory(candidate_id)
        result = service.embed_query("سلام")
        assert result.vector.ndim == 1
        assert result.vector.dtype == np.float32
        assert result.vector.shape[0] == service.model_info.dimension
        assert service.model_info.dimension > 0

    def test_m3_uses_heydari_backend(self):
        config = load_candidate_config("M3-persian-heydari", CANDIDATES_PATH, device="cpu")
        model = ModelRegistry.create(config)
        assert isinstance(model, HeydariPersianBackend)
        dimension = model.info.dimension
        assert dimension > 0

    def test_document_batching(self, service_factory):
        service = service_factory("M0-baseline")
        texts = [f"متن تست {index}" for index in range(5)]
        result = service.embed_documents(texts)
        assert len(result.vectors) == 5
        assert all(vec.shape[0] == service.model_info.dimension for vec in result.vectors)

    def test_invalid_cuda_device_raises(self):
        config = load_candidate_config("M0-baseline", CANDIDATES_PATH, device="cuda:99")
        with pytest.raises((EmbeddingDeviceError, EmbeddingModelLoadError)):
            ModelRegistry.create(config)
