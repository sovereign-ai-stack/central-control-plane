"""Benchmark metric and pipeline regression tests."""

from __future__ import annotations

import numpy as np
import pytest
from benchmarks.persian.metrics import (
    cosine_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

from rag.embedding.config import EmbeddingConfig
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel


class TestMetricFormulas:
    def test_recall_and_mrr_manual(self):
        relevant = {"D2"}
        ranked = ["D1", "D2", "D3"]
        assert recall_at_k(relevant, ranked, 1) == 0.0
        assert recall_at_k(relevant, ranked, 2) == 1.0
        assert reciprocal_rank(relevant, ranked) == 0.5
        assert precision_at_k(relevant, ranked, 2) == 0.5

    def test_multiple_relevant_docs(self):
        relevant = {"D1", "D3"}
        ranked = ["D1", "D4", "D3", "D2"]
        assert recall_at_k(relevant, ranked, 1) == 1.0
        assert recall_at_k(relevant, ranked, 2) == 1.0
        assert precision_at_k(relevant, ranked, 3) == pytest.approx(2 / 3)
        assert ndcg_at_k(relevant, ranked, 3) > 0.0

    def test_cosine_rank_known_vectors(self):
        same = np.array([1.0, 0.0], dtype=np.float32)
        opposite = np.array([-1.0, 0.0], dtype=np.float32)
        orth = np.array([0.0, 1.0], dtype=np.float32)
        matrix = np.vstack([orth, opposite, same])
        doc_ids = ["orth", "opposite", "same"]
        ranked = cosine_rank(same, doc_ids, matrix)
        assert ranked[0] == "same"
        assert ranked[-1] == "opposite"


class TestControlExperiments:
    def test_exact_text_query_ranks_first_with_stub(self):
        docs = ["سیاست مرخصی سالانه ۱۰ روز", "متن نامرتبط درباره VPN"]
        query = docs[0]
        model = StubEmbeddingModel(dimension=64)
        service = EmbeddingService(model, EmbeddingPreprocessor())
        doc_matrix = np.vstack(service.embed_documents(docs).vectors)
        query_vec = service.embed_query(query).vector
        ranked = cosine_rank(query_vec, ["d1", "d2"], doc_matrix)
        assert ranked[0] == "d1"

    def test_normalized_exact_text_with_stub(self):
        raw_doc = "علي   كتاب"
        raw_query = "علي كتاب"
        model = StubEmbeddingModel(dimension=64)
        service = EmbeddingService(model, EmbeddingPreprocessor())
        doc_matrix = np.vstack(service.embed_documents([raw_doc]).vectors)
        query_vec = service.embed_query(raw_query).vector
        ranked = cosine_rank(query_vec, ["d1"], doc_matrix)
        assert ranked[0] == "d1"

    def test_e5_prefixes_applied(self):
        config = EmbeddingConfig(
            backend="stub",
            model_id="stub-v1",
            query_prefix="query: ",
            document_prefix="passage: ",
        )
        model = ModelRegistry.create(config)
        assert isinstance(model, StubEmbeddingModel)
        # Prefixes on stub are ignored — verify ST backend applies via unit on backend class
        from rag.embedding.backends.sentence_transformers import SentenceTransformersBackend

        backend = SentenceTransformersBackend.__new__(SentenceTransformersBackend)
        backend._config = config
        assert backend._apply_prefix("test", is_query=True) == "query: test"
        assert backend._apply_prefix("test", is_query=False) == "passage: test"
