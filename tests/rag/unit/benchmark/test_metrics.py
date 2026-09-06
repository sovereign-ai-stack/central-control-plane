"""Hand-calculated retrieval metric regression tests."""

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


class TestRetrievalMetrics:
    def test_recall_and_mrr_single_relevant(self):
        relevant = {"D2"}
        ranked = ["D1", "D2", "D3"]
        assert recall_at_k(relevant, ranked, 1) == 0.0
        assert recall_at_k(relevant, ranked, 2) == 1.0
        assert reciprocal_rank(relevant, ranked) == 0.5

    def test_recall_multiple_relevant(self):
        relevant = {"D2", "D4"}
        ranked = ["D1", "D2", "D3", "D4"]
        assert recall_at_k(relevant, ranked, 1) == 0.0
        assert recall_at_k(relevant, ranked, 2) == 1.0
        assert recall_at_k(relevant, ranked, 4) == 1.0

    def test_precision_at_k(self):
        relevant = {"D2", "D4"}
        ranked = ["D1", "D2", "D3", "D4", "D5"]
        assert precision_at_k(relevant, ranked, 5) == pytest.approx(0.4)

    def test_ndcg_at_k(self):
        relevant = {"D2"}
        ranked = ["D1", "D2", "D3"]
        expected = (1.0 / np.log2(3)) / 1.0
        assert ndcg_at_k(relevant, ranked, 2) == pytest.approx(expected)

    def test_cosine_rank_ordering(self):
        query = np.array([1.0, 0.0], dtype=np.float32)
        docs = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]], dtype=np.float32)
        ranked = cosine_rank(query, ["same", "orth", "opposite"], docs)
        assert ranked[0] == "same"
        assert ranked[-1] == "opposite"

    def test_cosine_known_values(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0], dtype=np.float32)
        c = np.array([-1.0, 0.0], dtype=np.float32)
        d = np.array([0.0, 1.0], dtype=np.float32)
        assert pytest.approx(float(a @ b)) == 1.0
        assert pytest.approx(float(a @ c)) == -1.0
        assert pytest.approx(float(a @ d)) == 0.0
