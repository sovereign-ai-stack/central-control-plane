"""
Top-K selection with a context token budget (spec 005-rag-pipeline/interface.md §4).

Ordering is fully deterministic (see `ordering.py`). The budget is filled
greedily in that order using the *same* block rendering the context builder
uses, so the selected set and the assembled context can never disagree.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from rag.contracts.retrieval import RetrievedChunk
from rag.pipeline.context_builder import assemble_text, citation_id, render_source_block
from rag.pipeline.errors import PipelineValidationError
from rag.pipeline.ordering import order_final
from rag.pipeline.tokenizer import TokenCounter
from rag.pipeline.types import TopKResult


class TopKSelector:
    def select(
        self,
        candidates: Sequence[RetrievedChunk],
        *,
        top_k: int,
        max_context_tokens: int,
        token_counter: TokenCounter,
        rerank_scores: Mapping[UUID, float] | None = None,
    ) -> TopKResult:
        if top_k <= 0:
            raise PipelineValidationError("top_k must be positive")
        if max_context_tokens <= 0:
            raise PipelineValidationError("max_context_tokens must be positive")

        ordered = order_final(list(candidates), rerank_scores or {})
        head = ordered[:top_k]
        dropped_for_top_k = tuple(chunk.chunk_id for chunk in ordered[top_k:])

        selected: list[RetrievedChunk] = []
        blocks: list[str] = []
        dropped_for_budget: list[UUID] = []

        for position, chunk in enumerate(head):
            block = render_source_block(chunk, citation_id(len(selected)))
            candidate_text = assemble_text([*blocks, block])
            if token_counter.count(candidate_text) > max_context_tokens:
                # Budget exhausted: drop this chunk and every lower-priority one,
                # so the retained prefix always matches the ranking order.
                dropped_for_budget.extend(item.chunk_id for item in head[position:])
                break
            selected.append(chunk)
            blocks.append(block)

        return TopKResult(
            selected=tuple(selected),
            dropped_for_top_k=dropped_for_top_k,
            dropped_for_token_budget=tuple(dropped_for_budget),
        )
