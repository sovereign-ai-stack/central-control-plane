"""FUNC-EMB-* embedding service unit tests."""

from __future__ import annotations

import numpy as np
import pytest

from rag.embedding.config import EmbeddingConfig, load_embedding_config
from rag.embedding.errors import (
    EmbeddingDimensionMismatch,
    EmbeddingValidationError,
)
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.embedding.validation import validate_vector_store_dimension
from rag.ingestion.persian import normalize_persian


@pytest.fixture
def stub_model() -> StubEmbeddingModel:
    return StubEmbeddingModel(dimension=384, model_id="stub-v1")


@pytest.fixture
def embedding_service(stub_model: StubEmbeddingModel) -> EmbeddingService:
    return EmbeddingService(stub_model, EmbeddingPreprocessor())


class TestEmbeddingService:
    def test_func_emb_001_query_dimension(self, embedding_service: EmbeddingService):
        result = embedding_service.embed_query("سلام دنیا")
        assert result.vector.shape == (384,)
        assert result.vector.dtype == np.float32

    def test_func_emb_002_batch_order(self, embedding_service: EmbeddingService):
        texts = ["اول", "دوم", "سوم"]
        result = embedding_service.embed_documents(texts)
        assert len(result.vectors) == 3
        singles = [embedding_service.embed_documents([text]).vectors[0] for text in texts]
        for batch_vec, single_vec in zip(result.vectors, singles, strict=True):
            assert np.allclose(batch_vec, single_vec)

    def test_func_emb_003_deterministic(self, embedding_service: EmbeddingService):
        first = embedding_service.embed_query("متن ثابت")
        second = embedding_service.embed_query("متن ثابت")
        assert np.allclose(first.vector, second.vector)

    def test_func_emb_004_same_model_for_query_and_document(
        self, embedding_service: EmbeddingService
    ):
        query = embedding_service.embed_query("همان متن")
        document = embedding_service.embed_documents(["همان متن"]).vectors[0]
        assert np.allclose(query.vector, document)

    def test_func_emb_005_empty_text_rejected(self, embedding_service: EmbeddingService):
        with pytest.raises(EmbeddingValidationError):
            embedding_service.embed_query("   ")

    def test_func_emb_006_preprocessing_before_embed(
        self, embedding_service: EmbeddingService
    ):
        raw = "علي   كتاب"
        result = embedding_service.embed_query(raw)
        normalized = normalize_persian(raw)
        expected = embedding_service.embed_query(normalized)
        assert np.allclose(result.vector, expected.vector)

    def test_func_emb_007_stub_available_via_registry(self):
        config = EmbeddingConfig(backend="stub", model_id="stub-v1")
        model = ModelRegistry.create(config)
        assert isinstance(model, StubEmbeddingModel)
        assert model.health_check()

    def test_func_emb_008_empty_batch(self, embedding_service: EmbeddingService):
        result = embedding_service.embed_documents([])
        assert result.vectors == []
        assert result.batch_size == 0

    def test_l2_normalization(self, embedding_service: EmbeddingService):
        vector = embedding_service.embed_query("نرمال سازی").vector
        norm = float(np.linalg.norm(vector))
        assert abs(norm - 1.0) < 1e-5

    def test_dimension_validation_passes(self, stub_model: StubEmbeddingModel):
        validate_vector_store_dimension(stub_model.info, 384)

    def test_dimension_validation_fails(self, stub_model: StubEmbeddingModel):
        with pytest.raises(EmbeddingDimensionMismatch):
            validate_vector_store_dimension(stub_model.info, 512)

    def test_startup_dimension_check(self, stub_model: StubEmbeddingModel):
        EmbeddingService(stub_model, vector_store_dimension=384)

    def test_startup_dimension_mismatch(self, stub_model: StubEmbeddingModel):
        with pytest.raises(EmbeddingDimensionMismatch):
            EmbeddingService(stub_model, vector_store_dimension=512)

    def test_load_default_config(self):
        """
        The shipped config is the production selection (BAAI/bge-m3).

        This assertion was previously `backend == "stub"`, which encoded the
        pre-selection state. Full coverage of the selection lives in
        tests/integration/embedding/test_production_model.py.
        """
        config = load_embedding_config()
        assert config.backend == "sentence-transformers"
        assert config.model_id == "BAAI/bge-m3"
        assert config.production is True
        assert config.revision is not None, "production revision must be pinned"
