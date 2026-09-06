"""ModelRegistry and configuration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.embedding.config import EmbeddingConfig, load_candidate_config
from rag.embedding.errors import EmbeddingModelLoadError
from rag.embedding.registry import ModelRegistry

CANDIDATES_PATH = (
    Path(__file__).resolve().parents[4] / "benchmarks" / "persian" / "config" / "candidates.yaml"
)


class TestModelRegistry:
    def test_list_backends(self):
        assert ModelRegistry.list_registered_backends() == ["stub", "sentence-transformers"]

    def test_create_stub(self):
        model = ModelRegistry.create(EmbeddingConfig(backend="stub", model_id="stub-v1"))
        assert model.health_check()

    def test_unknown_backend(self):
        with pytest.raises(EmbeddingModelLoadError):
            ModelRegistry.create(EmbeddingConfig(backend="unknown", model_id="x"))

    def test_load_m3_candidate_config(self):
        config = load_candidate_config("M3-persian-heydari", CANDIDATES_PATH)
        assert config.production is False
        assert config.query_prefix is None

    def test_config_driven_candidate_reference(self):
        config = load_candidate_config("M0-baseline", CANDIDATES_PATH)
        assert config.backend == "sentence-transformers"
        assert config.model_id.endswith("MiniLM-L12-v2")
        assert config.production is False
