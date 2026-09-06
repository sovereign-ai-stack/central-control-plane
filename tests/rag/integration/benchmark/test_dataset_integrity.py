"""Dataset ground-truth integrity tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from benchmarks.persian.dataset import load_dataset, query_category
from benchmarks.persian.generate_dataset import generate_dataset
from benchmarks.persian.validate_dataset import validate_dataset

from rag.ingestion.persian import normalize_persian

DATASET_DIR = Path(__file__).resolve().parents[4] / "benchmarks" / "persian" / "data" / "fa-retrieval-v1"


@pytest.fixture(scope="module", autouse=True)
def ensure_fresh_dataset() -> None:
    generate_dataset(DATASET_DIR)


class TestDatasetGroundTruth:
    def test_validation_passes(self):
        assert validate_dataset(DATASET_DIR) == []

    def test_no_title_only_semantic_queries(self):
        dataset = load_dataset(DATASET_DIR)
        corpus = {doc.doc_id: doc.text for doc in dataset.corpus}
        for query in dataset.queries:
            if query.query_id not in dataset.validation_query_ids:
                continue
            if query_category(query) != "semantic":
                continue
            doc_text = corpus[query.relevant_doc_ids[0]]
            normalized_query = normalize_persian(query.text)
            normalized_doc = normalize_persian(doc_text)
            assert "اطلاعات درباره" not in normalized_query
            shared_tokens = set(normalized_query.split()) & set(normalized_doc.split())
            assert len(shared_tokens) >= 1, (
                f"semantic query has no token overlap with labeled doc: {query.text!r}"
            )

    def test_zwnj_queries_reference_document_topic(self):
        dataset = load_dataset(DATASET_DIR)
        corpus = {doc.doc_id: doc.text for doc in dataset.corpus}
        zwnj_queries = [
            q
            for q in dataset.queries
            if q.query_id in dataset.validation_query_ids and q.normalization == "zwnj"
        ]
        assert len(zwnj_queries) >= 10
        for query in zwnj_queries[:10]:
            doc_text = corpus[query.relevant_doc_ids[0]]
            query_norm = normalize_persian(query.text)
            doc_norm = normalize_persian(doc_text)
            assert any(token in doc_norm for token in query_norm.split() if len(token) > 2)
