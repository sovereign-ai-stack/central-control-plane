"""Dataset grounding and control experiment regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from benchmarks.persian.dataset import load_dataset, query_category
from benchmarks.persian.evaluate import encode_corpus, rank_query
from benchmarks.persian.metrics import recall_at_k
from benchmarks.persian.validate_dataset import validate_dataset

from rag.embedding.config import load_candidate_config
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.ingestion.persian import normalize_persian

REPO = Path(__file__).resolve().parents[4]
DATASET = REPO / "benchmarks" / "persian" / "data" / "fa-retrieval-v1"
CANDIDATES = REPO / "benchmarks" / "persian" / "config" / "candidates.yaml"


@pytest.fixture(scope="module")
def dataset():
    if not (DATASET / "corpus.jsonl").exists():
        from benchmarks.persian.generate_dataset import generate_dataset

        generate_dataset(DATASET)
    return load_dataset(DATASET)


@pytest.fixture(scope="module")
def stub_service():
    config = load_candidate_config("M0-baseline", CANDIDATES, device="cpu")
    model = ModelRegistry.create(config)
    return EmbeddingService(model, EmbeddingPreprocessor())


class TestDatasetGrounding:
    def test_validation_passes(self, dataset):
        assert validate_dataset(DATASET) == []

    def test_validation_queries_have_category(self, dataset):
        val = [q for q in dataset.queries if q.query_id in dataset.validation_query_ids]
        assert all(q.category for q in val)

    def test_ungrounded_title_query_would_fail_recall_at_5(self, stub_service, dataset):
        """Regression for the original benchmark bug: title-only queries are not retrievable."""
        doc = dataset.corpus[0]
        doc_ids, doc_matrix, corpus_text = encode_corpus(stub_service, dataset)
        bad_query = f"اطلاعات درباره {doc.doc_id[:8]}"
        ranked, _ = rank_query(stub_service, bad_query, doc_ids, doc_matrix, corpus_text)
        assert recall_at_k({doc.doc_id}, ranked, 5) == 0.0

    def test_grounded_semantic_query_hits_recall_at_5(self, stub_service, dataset):
        val = [q for q in dataset.queries if q.query_id in dataset.validation_query_ids]
        semantic = next(q for q in val if query_category(q) == "semantic")
        doc_ids, doc_matrix, corpus_text = encode_corpus(stub_service, dataset)
        ranked, _ = rank_query(stub_service, semantic.text, doc_ids, doc_matrix, corpus_text)
        assert recall_at_k(set(semantic.relevant_doc_ids), ranked, 5) == 1.0

    def test_exact_document_ranks_first(self, stub_service, dataset):
        doc = dataset.corpus[0]
        doc_ids, doc_matrix, corpus_text = encode_corpus(stub_service, dataset)
        ranked, _ = rank_query(stub_service, doc.text, doc_ids, doc_matrix, corpus_text)
        assert ranked[0] == doc.doc_id

    def test_normalized_exact_document_ranks_first(self, stub_service, dataset):
        doc = dataset.corpus[0]
        doc_ids, doc_matrix, corpus_text = encode_corpus(stub_service, dataset)
        ranked, _ = rank_query(
            stub_service, normalize_persian(doc.text), doc_ids, doc_matrix, corpus_text
        )
        assert ranked[0] == doc.doc_id

    @pytest.mark.parametrize(
        ("raw", "expected_fragment"),
        [
            ("علي كتاب", "علی"),
            ("می\u200cخواهم", "می"),
        ],
    )
    def test_persian_normalization(self, raw, expected_fragment):
        normalized = normalize_persian(raw)
        assert expected_fragment in normalized
