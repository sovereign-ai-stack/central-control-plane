"""
Unit tests for the reranker abstraction (spec 005-rag-pipeline/reranker.md §8).

Covers RR-T01..RR-T05 and PP-010..PP-013.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from tests.rag.conftest import make_retrieved_chunk

from rag.pipeline.errors import RerankContractViolationError
from rag.pipeline.reranker import (
    LexicalReranker,
    NoOpReranker,
    Reranker,
    merge_rerank_scores,
    select_rerank_window,
    validate_rerank_contract,
)
from rag.pipeline.types import RerankResult

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


class TestNoOpReranker:
    def test_rr_t01_preserves_order_and_ids(self):
        candidates = [_chunk(f"chunk {index}", 0.9 - index * 0.1) for index in range(5)]
        result = NoOpReranker().rerank("query", candidates)
        assert [c.chunk_id for c in result.candidates] == [
            c.chunk_id for c in candidates
        ]
        assert result.model_id is None
        assert result.rerank_scores == {}

    def test_rr_t06_zero_latency_passthrough(self):
        result = NoOpReranker().rerank("query", [_chunk("a", 0.5)])
        assert result.latency_ms == 0

    def test_rr_t05_empty_candidates(self):
        result = NoOpReranker().rerank("query", [])
        assert result.candidates == ()
        assert result.rerank_scores == {}

    def test_satisfies_reranker_protocol(self):
        assert isinstance(NoOpReranker(), Reranker)
        assert isinstance(LexicalReranker(), Reranker)


class TestLexicalReranker:
    def test_rr_t02_reorders_with_same_id_set(self):
        query = "مرخصی سالانه"
        semantic_leader = _chunk("راهنمای فنی سرور و پورت", 0.90)
        lexical_winner = _chunk("کارکنان حق مرخصی سالانه دارند.", 0.80)
        result = LexicalReranker().rerank(query, [semantic_leader, lexical_winner])

        assert result.candidates[0].chunk_id == lexical_winner.chunk_id
        assert {c.chunk_id for c in result.candidates} == {
            semantic_leader.chunk_id,
            lexical_winner.chunk_id,
        }
        assert result.model_id == "lexical-rerank-v1"

    def test_score_formula_is_explicit(self):
        reranker = LexicalReranker(
            retrieval_weight=0.5, lexical_weight=0.3, phrase_weight=0.2
        )
        chunk = _chunk("مرخصی سالانه برای کارکنان", 0.8)
        result = reranker.rerank("مرخصی سالانه", [chunk])
        expected = 0.5 * 0.8 + 0.3 * 1.0 + 0.2 * 1.0
        assert result.rerank_scores[chunk.chunk_id] == pytest.approx(expected)

    def test_deterministic_across_runs(self):
        query = "مرخصی سالانه"
        candidates = [
            _chunk("مرخصی سالانه", 0.5),
            _chunk("سیاست مرخصی", 0.5),
            _chunk("راهنمای فنی", 0.5),
        ]
        first = LexicalReranker().rerank(query, candidates)
        second = LexicalReranker().rerank(query, candidates)
        assert [c.chunk_id for c in first.candidates] == [
            c.chunk_id for c in second.candidates
        ]

    def test_tie_break_is_stable_on_metadata(self):
        document_id = uuid4()
        low_index = _chunk("same text", 0.5, document_id=document_id, chunk_index=0)
        high_index = _chunk("same text", 0.5, document_id=document_id, chunk_index=1)
        result = LexicalReranker().rerank("unrelated", [high_index, low_index])
        assert [c.chunk_index for c in result.candidates] == [0, 1]

    def test_empty_candidates(self):
        result = LexicalReranker().rerank("query", [])
        assert result.candidates == ()


class TestRerankContract:
    def test_rr_t04_extra_chunk_rejected(self):
        inputs = [_chunk("a", 0.9)]
        output = RerankResult(
            candidates=(inputs[0], _chunk("smuggled", 0.99)),
            rerank_scores={},
            latency_ms=0,
            model_id="malicious",
        )
        with pytest.raises(RerankContractViolationError):
            validate_rerank_contract(inputs, output)

    def test_dropped_chunk_rejected(self):
        inputs = [_chunk("a", 0.9), _chunk("b", 0.8)]
        output = RerankResult(
            candidates=(inputs[0],),
            rerank_scores={},
            latency_ms=0,
            model_id="malicious",
        )
        with pytest.raises(RerankContractViolationError):
            validate_rerank_contract(inputs, output)

    def test_substituted_chunk_rejected(self):
        inputs = [_chunk("a", 0.9)]
        output = RerankResult(
            candidates=(_chunk("substituted", 0.9),),
            rerank_scores={},
            latency_ms=0,
            model_id="malicious",
        )
        with pytest.raises(RerankContractViolationError):
            validate_rerank_contract(inputs, output)

    def test_scores_for_unknown_chunks_rejected(self):
        inputs = [_chunk("a", 0.9)]
        output = RerankResult(
            candidates=(inputs[0],),
            rerank_scores={uuid4(): 1.0},
            latency_ms=0,
            model_id="malicious",
        )
        with pytest.raises(RerankContractViolationError):
            validate_rerank_contract(inputs, output)

    def test_valid_reorder_accepted(self):
        inputs = [_chunk("a", 0.9), _chunk("b", 0.8)]
        output = RerankResult(
            candidates=(inputs[1], inputs[0]),
            rerank_scores={inputs[0].chunk_id: 0.4},
            latency_ms=1,
            model_id="lexical-rerank-v1",
        )
        validate_rerank_contract(inputs, output)

    def test_rr_t04_real_rerankers_satisfy_contract(self):
        candidates = [_chunk(f"چانک {index}", 0.9 - index * 0.05) for index in range(50)]
        for reranker in (NoOpReranker(), LexicalReranker()):
            result = reranker.rerank("چانک", candidates)
            validate_rerank_contract(candidates, result)
            assert len(result.candidates) == 50


class TestRerankWindow:
    def test_window_caps_input_by_retrieval_score(self):
        candidates = [_chunk(f"c{index}", index / 100) for index in range(10)]
        window, remainder = select_rerank_window(candidates, 3)
        assert len(window) == 3
        assert len(remainder) == 7
        assert [c.score for c in window] == [0.09, 0.08, 0.07]

    def test_window_returns_all_when_under_cap(self):
        candidates = [_chunk("a", 0.5), _chunk("b", 0.4)]
        window, remainder = select_rerank_window(candidates, 10)
        assert len(window) == 2
        assert remainder == []

    def test_remainder_keeps_no_rerank_score(self):
        candidates = [_chunk(f"c{index}", index / 100) for index in range(5)]
        window, remainder = select_rerank_window(candidates, 2)
        scored = LexicalReranker().rerank("c", candidates)
        merged = merge_rerank_scores(scored.rerank_scores, remainder)
        assert all(chunk.chunk_id in merged for chunk in window)
        assert all(chunk.chunk_id not in merged for chunk in remainder)
