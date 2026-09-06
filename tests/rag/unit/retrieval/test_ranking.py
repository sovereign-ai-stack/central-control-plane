"""Unit tests for retrieval ranking."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from rag.retrieval.errors import RetrievalDimensionMismatchError
from rag.retrieval.ranking import cosine_similarity, rank_by_similarity


class TestCosineSimilarity:
    def test_identical_vectors_score_one(self) -> None:
        vector = np.array([1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(vector, vector) == pytest.approx(1.0)

    def test_orthogonal_vectors_score_zero(self) -> None:
        query = np.array([1.0, 0.0], dtype=np.float32)
        document = np.array([0.0, 1.0], dtype=np.float32)
        assert cosine_similarity(query, document) == pytest.approx(0.0)

    def test_dimension_mismatch_raises(self) -> None:
        query = np.array([1.0, 0.0], dtype=np.float32)
        document = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        with pytest.raises(RetrievalDimensionMismatchError):
            cosine_similarity(query, document)


class TestRankBySimilarity:
    def test_orders_by_score_then_chunk_id(self) -> None:
        low_id = uuid4()
        high_id = uuid4()
        if str(low_id) > str(high_id):
            low_id, high_id = high_id, low_id

        items = [
            ("b", 0.5, high_id),
            ("a", 1.0, low_id),
            ("c", 0.5, low_id if high_id != low_id else high_id),
        ]
        ranked = rank_by_similarity(items, top_k=3)
        assert ranked[0][0] == "a"
        assert ranked[0][1] == pytest.approx(1.0)

    def test_top_k_limits_results(self) -> None:
        items = [(f"item-{index}", float(index), uuid4()) for index in range(5)]
        ranked = rank_by_similarity(items, top_k=2)
        assert len(ranked) == 2
