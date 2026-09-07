"""ModelRegistry and configuration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag.embedding.backends.jina_v5 import JinaEmbeddingsV5Backend
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


class TestStrictLoad:
    """A failed load must not be papered over when the caller is measuring."""

    def _unloadable(self, *, strict: bool) -> EmbeddingConfig:
        # cuda:99 fails in the loader before any download is attempted.
        return EmbeddingConfig(
            backend="sentence-transformers",
            model_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            device="cuda:99",
            strict_load=strict,
        )

    def test_strict_load_raises_instead_of_stub(self):
        with pytest.raises(EmbeddingModelLoadError):
            ModelRegistry.create(self._unloadable(strict=True))

    def test_default_keeps_serving_stub_fallback(self):
        model = ModelRegistry.create(self._unloadable(strict=False))
        assert model.info.backend == "stub"


class TestJinaV5Candidate:
    """M4 wiring, asserted without loading the checkpoint."""

    def test_candidate_config_uses_official_retrieval_prompts(self):
        config = load_candidate_config("M4-jina-v5-nano", CANDIDATES_PATH)
        assert config.model_id == "jinaai/jina-embeddings-v5-text-nano"
        assert config.query_prefix == "Query: "
        assert config.document_prefix == "Document: "
        assert config.production is False

    def test_benchmark_load_settings_apply_to_every_candidate(self):
        for candidate_id in (
            "M0-baseline",
            "M1-e5-large",
            "M2-bge-m3",
            "M3-persian-heydari",
            "M4-jina-v5-nano",
        ):
            config = load_candidate_config(candidate_id, CANDIDATES_PATH)
            assert config.strict_load is True
            assert config.load_timeout_sec == 900.0

    def test_retrieval_adapter_is_selected_at_load(self):
        config = load_candidate_config("M4-jina-v5-nano", CANDIDATES_PATH)
        kwargs = JinaEmbeddingsV5Backend._sentence_transformer_kwargs(config)
        assert kwargs["trust_remote_code"] is True
        assert kwargs["model_kwargs"]["default_task"] == "retrieval"

    def test_rejects_a_foreign_model_id(self):
        config = load_candidate_config("M0-baseline", CANDIDATES_PATH)
        with pytest.raises(EmbeddingModelLoadError):
            JinaEmbeddingsV5Backend(config)
