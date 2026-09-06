"""
Unit tests for post-retrieval deduplication (spec 005 PP-020..PP-022).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from tests.rag.conftest import make_retrieved_chunk

from rag.pipeline.deduplicator import ChunkDeduplicator, normalized_content_hash

COMPANY = UUID("11111111-1111-1111-1111-111111111101")
DEPARTMENT = UUID("22222222-2222-2222-2222-222222222201")


def _chunk(content: str, score: float, **kwargs):
    return make_retrieved_chunk(
        content,
        score=score,
        company_id=COMPANY,
        department_id=DEPARTMENT,
        **kwargs,
    )


class TestDeduplicationByChunkId:
    def test_pp_020_duplicate_chunk_id_removed(self):
        chunk_id = uuid4()
        first = _chunk("body", 0.9, chunk_id=chunk_id)
        second = _chunk("body", 0.5, chunk_id=chunk_id)
        result = ChunkDeduplicator().deduplicate([first, second])
        assert len(result.chunks) == 1
        assert result.removed_duplicate_ids == (chunk_id,)

    def test_highest_score_instance_wins(self):
        chunk_id = uuid4()
        low = _chunk("body", 0.4, chunk_id=chunk_id)
        high = _chunk("body", 0.95, chunk_id=chunk_id)
        result = ChunkDeduplicator().deduplicate([low, high])
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.95

    def test_rerank_score_decides_the_winner(self):
        chunk_id = uuid4()
        low_retrieval = _chunk("body", 0.4, chunk_id=chunk_id)
        high_retrieval = _chunk("body", 0.95, chunk_id=chunk_id)
        result = ChunkDeduplicator().deduplicate(
            [low_retrieval, high_retrieval],
            rerank_scores={chunk_id: 0.7},
        )
        # Both instances share the chunk_id, so the rerank score ties them and
        # the first occurrence is kept.
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.4


class TestDeduplicationByContentHash:
    def test_pp_021_same_normalized_content_removed(self):
        zwnj = "‌"
        first = _chunk(f"مرخصی{zwnj}سالانه", 0.9)
        second = _chunk("مرخصی سالانه", 0.5)
        result = ChunkDeduplicator().deduplicate([first, second])
        assert len(result.chunks) == 1
        assert result.removed_near_duplicate_ids == (second.chunk_id,)

    def test_highest_score_near_duplicate_kept(self):
        first = _chunk("shared text", 0.4)
        second = _chunk("shared text", 0.95)
        result = ChunkDeduplicator().deduplicate([first, second])
        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == second.chunk_id

    def test_distinct_content_preserved(self):
        document_id = uuid4()
        first = _chunk("chunk one", 0.9, document_id=document_id, chunk_index=0)
        second = _chunk("chunk two", 0.8, document_id=document_id, chunk_index=1)
        result = ChunkDeduplicator().deduplicate([first, second])
        assert len(result.chunks) == 2

    def test_content_hash_dedupe_can_be_disabled(self):
        first = _chunk("shared text", 0.9)
        second = _chunk("shared text", 0.5)
        result = ChunkDeduplicator().deduplicate(
            [first, second], by_content_hash=False
        )
        assert len(result.chunks) == 2

    def test_hash_reuses_fa_norm_v1(self):
        zwnj = "‌"
        assert normalized_content_hash(f"مرخصی{zwnj}سالانه") == normalized_content_hash(
            "مرخصی سالانه"
        )


class TestDeduplicationOrdering:
    def test_survivor_order_preserves_input_order(self):
        first = _chunk("alpha", 0.9)
        second = _chunk("beta", 0.8)
        third = _chunk("gamma", 0.7)
        result = ChunkDeduplicator().deduplicate([first, second, third])
        assert [c.chunk_id for c in result.chunks] == [
            first.chunk_id,
            second.chunk_id,
            third.chunk_id,
        ]

    def test_pp_022_counts_are_accurate(self):
        chunk_id = uuid4()
        candidates = [
            _chunk("body", 0.9, chunk_id=chunk_id),
            _chunk("body", 0.8, chunk_id=chunk_id),
            _chunk("body", 0.7),
            _chunk("other", 0.6),
        ]
        result = ChunkDeduplicator().deduplicate(candidates)
        assert len(result.removed_duplicate_ids) == 1
        assert len(result.removed_near_duplicate_ids) == 1
        assert len(result.chunks) == 2

    def test_empty_input(self):
        result = ChunkDeduplicator().deduplicate([])
        assert result.chunks == ()
        assert result.removed_duplicate_ids == ()
        assert result.removed_near_duplicate_ids == ()

    def test_deterministic_across_runs(self):
        candidates = [_chunk(f"body {index}", 0.5) for index in range(5)]
        first = ChunkDeduplicator().deduplicate(candidates)
        second = ChunkDeduplicator().deduplicate(candidates)
        assert [c.chunk_id for c in first.chunks] == [c.chunk_id for c in second.chunks]
