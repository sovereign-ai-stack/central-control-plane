"""
Unit tests for top-K selection and the context token budget
(spec 005 PP-030..PP-033, interface.md §4).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from tests.rag.conftest import make_retrieved_chunk

from rag.pipeline.context_builder import assemble_text, citation_id, render_source_block
from rag.pipeline.errors import PipelineValidationError
from rag.pipeline.selector import TopKSelector
from rag.pipeline.tokenizer import CharEstimateTokenCounter

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


def _counter() -> CharEstimateTokenCounter:
    return CharEstimateTokenCounter(4)


def _generous_budget() -> int:
    return 100_000


class TestTopKLimit:
    def test_pp_030_top_k_limits_selection(self):
        candidates = [_chunk(f"body {index}", 0.9 - index * 0.01) for index in range(20)]
        result = TopKSelector().select(
            candidates,
            top_k=5,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
        )
        assert len(result.selected) == 5
        assert len(result.dropped_for_top_k) == 15

    def test_fewer_candidates_than_top_k(self):
        candidates = [_chunk("only", 0.9)]
        result = TopKSelector().select(
            candidates,
            top_k=10,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
        )
        assert len(result.selected) == 1
        assert result.dropped_for_top_k == ()

    def test_empty_candidates(self):
        result = TopKSelector().select(
            [],
            top_k=5,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
        )
        assert result.selected == ()

    def test_invalid_limits_rejected(self):
        with pytest.raises(PipelineValidationError):
            TopKSelector().select(
                [], top_k=0, max_context_tokens=100, token_counter=_counter()
            )
        with pytest.raises(PipelineValidationError):
            TopKSelector().select(
                [], top_k=5, max_context_tokens=0, token_counter=_counter()
            )


class TestDeterministicOrdering:
    def test_rerank_score_beats_retrieval_score(self):
        weak_retrieval = _chunk("a", 0.10)
        strong_retrieval = _chunk("b", 0.99)
        result = TopKSelector().select(
            [strong_retrieval, weak_retrieval],
            top_k=2,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
            rerank_scores={weak_retrieval.chunk_id: 0.95, strong_retrieval.chunk_id: 0.1},
        )
        assert result.selected[0].chunk_id == weak_retrieval.chunk_id

    def test_unscored_chunk_falls_back_to_retrieval_score(self):
        scored = _chunk("a", 0.10)
        unscored = _chunk("b", 0.80)
        result = TopKSelector().select(
            [scored, unscored],
            top_k=2,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
            rerank_scores={scored.chunk_id: 0.50},
        )
        assert result.selected[0].chunk_id == unscored.chunk_id

    def test_pp_032_tie_break_document_then_index_then_chunk_id(self):
        document_a = UUID("aaaaaaaa-0000-0000-0000-000000000001")
        document_b = UUID("bbbbbbbb-0000-0000-0000-000000000001")
        later = _chunk("x", 0.5, document_id=document_b, chunk_index=0)
        first = _chunk("y", 0.5, document_id=document_a, chunk_index=0)
        second = _chunk("z", 0.5, document_id=document_a, chunk_index=1)
        result = TopKSelector().select(
            [later, second, first],
            top_k=3,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
        )
        assert [c.chunk_id for c in result.selected] == [
            first.chunk_id,
            second.chunk_id,
            later.chunk_id,
        ]

    def test_pp_032_same_input_same_output(self):
        candidates = [_chunk(f"body {index}", 0.5) for index in range(10)]
        selector = TopKSelector()
        first = selector.select(
            candidates,
            top_k=4,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
        )
        second = selector.select(
            list(reversed(candidates)),
            top_k=4,
            max_context_tokens=_generous_budget(),
            token_counter=_counter(),
        )
        assert [c.chunk_id for c in first.selected] == [
            c.chunk_id for c in second.selected
        ]


class TestTokenBudget:
    def test_pp_031_budget_caps_selection(self):
        candidates = [_chunk("x" * 400, 0.9 - index * 0.01) for index in range(20)]
        single_block = assemble_text([render_source_block(candidates[0], citation_id(0))])
        budget = _counter().count(single_block)
        result = TopKSelector().select(
            candidates,
            top_k=20,
            max_context_tokens=budget,
            token_counter=_counter(),
        )
        assert len(result.selected) == 1
        assert len(result.dropped_for_token_budget) == 19

    def test_pp_sec_051_all_chunks_dropped_for_budget(self):
        candidates = [_chunk("x" * 4000, 0.9) for _ in range(3)]
        result = TopKSelector().select(
            candidates,
            top_k=3,
            max_context_tokens=1,
            token_counter=_counter(),
        )
        assert result.selected == ()
        assert len(result.dropped_for_token_budget) == 3

    def test_pp_sec_052_single_chunk_fills_budget(self):
        chunk = _chunk("x" * 400, 0.9)
        block = assemble_text([render_source_block(chunk, citation_id(0))])
        result = TopKSelector().select(
            [chunk],
            top_k=5,
            max_context_tokens=_counter().count(block),
            token_counter=_counter(),
        )
        assert len(result.selected) == 1
        assert result.dropped_for_token_budget == ()

    def test_budget_drops_the_lowest_priority_tail(self):
        high = _chunk("x" * 400, 0.99)
        low = _chunk("y" * 400, 0.10)
        block = assemble_text([render_source_block(high, citation_id(0))])
        result = TopKSelector().select(
            [low, high],
            top_k=2,
            max_context_tokens=_counter().count(block),
            token_counter=_counter(),
        )
        assert [c.chunk_id for c in result.selected] == [high.chunk_id]
        assert result.dropped_for_token_budget == (low.chunk_id,)

    def test_pp_033_dropped_ids_are_disjoint_and_complete(self):
        candidates = [_chunk("x" * 400, 0.9 - index * 0.01) for index in range(10)]
        single_block = assemble_text([render_source_block(candidates[0], citation_id(0))])
        result = TopKSelector().select(
            candidates,
            top_k=4,
            max_context_tokens=_counter().count(single_block),
            token_counter=_counter(),
        )
        selected_ids = {c.chunk_id for c in result.selected}
        dropped = set(result.dropped_for_top_k) | set(result.dropped_for_token_budget)
        assert selected_ids.isdisjoint(dropped)
        assert selected_ids | dropped == {c.chunk_id for c in candidates}


class TestTokenCounter:
    def test_deterministic_and_monotonic(self):
        counter = CharEstimateTokenCounter(4)
        assert counter.count("") == 0
        assert counter.count("abcd") == 1
        assert counter.count("abcde") == 2
        assert counter.count("x" * 400) == 100

    def test_rejects_invalid_divisor(self):
        with pytest.raises(PipelineValidationError):
            CharEstimateTokenCounter(0)
