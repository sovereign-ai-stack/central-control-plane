"""
Reranker abstraction for already-authorized candidates (spec 005-rag-pipeline/reranker.md).

Security invariants enforced here:

- RR-001 input and output carry an identical `chunk_id` multiset
- RR-002 no vector store or retrieval engine access (this module imports neither)
- RR-003 no embedding or document fetching
- RR-004 no `AuthorizationContext` parameter, so scope cannot be widened
- RR-005 no authorization filtering (already done at retrieval)
- RR-006 `NoOpReranker` is a pass-through

`CrossEncoderReranker` is intentionally absent: reranker.md §4.2 defers the
production model to a benchmark, so no ML dependency is introduced here.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from rag.contracts.retrieval import RetrievedChunk
from rag.pipeline.errors import RerankContractViolationError
from rag.pipeline.ordering import order_by_retrieval
from rag.pipeline.types import RerankResult
from rag.retrieval.lexical import phrase_match_score, token_overlap_score


@runtime_checkable
class Reranker(Protocol):
    """Reorders authorized candidates only. Never retrieves, embeds, or filters."""

    @property
    def model_id(self) -> str | None:
        ...

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> RerankResult:
        ...


def validate_rerank_contract(
    inputs: Sequence[RetrievedChunk],
    output: RerankResult,
) -> None:
    """
    Assert RR-001: identical chunk_id multiset in and out.

    Raises RerankContractViolationError so callers fail closed instead of
    returning chunks a reranker may have introduced or dropped.
    """
    if len(inputs) != len(output.candidates):
        raise RerankContractViolationError(
            f"reranker changed candidate count: {len(inputs)} in, "
            f"{len(output.candidates)} out"
        )
    before = Counter(chunk.chunk_id for chunk in inputs)
    after = Counter(chunk.chunk_id for chunk in output.candidates)
    if before != after:
        raise RerankContractViolationError(
            "reranker changed the candidate chunk_id multiset"
        )
    unknown = set(output.rerank_scores) - set(before)
    if unknown:
        raise RerankContractViolationError(
            "reranker scored chunk_ids that were not in its input"
        )


def select_rerank_window(
    candidates: Sequence[RetrievedChunk],
    max_candidates: int,
) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:
    """
    Split candidates into the rerank window and the untouched remainder.

    Per reranker.md §6, when more candidates than `max_candidates` arrive, only
    the top `max_candidates` by retrieval score are reranked; the rest keep their
    retrieval order and receive no rerank score.
    """
    ordered = order_by_retrieval(list(candidates))
    if max_candidates <= 0 or len(ordered) <= max_candidates:
        return ordered, []
    return ordered[:max_candidates], ordered[max_candidates:]


class NoOpReranker:
    """Default reranker: preserves retrieval order, assigns no rerank scores."""

    @property
    def model_id(self) -> str | None:
        return None

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> RerankResult:
        _ = query
        return RerankResult(
            candidates=tuple(candidates),
            rerank_scores={},
            latency_ms=0,
            model_id=None,
        )


class LexicalReranker:
    """
    Deterministic reranker usable in tests without downloading a model.

    rerank_score =
        retrieval_weight * retrieval_score
      + lexical_weight   * token_overlap
      + phrase_weight    * phrase_match

    Lexical scoring reuses the fa-norm-v1 helpers from `rag.retrieval.lexical`;
    no second normalizer is introduced.
    """

    MODEL_ID = "lexical-rerank-v1"

    def __init__(
        self,
        *,
        retrieval_weight: float = 0.5,
        lexical_weight: float = 0.3,
        phrase_weight: float = 0.2,
    ) -> None:
        self._retrieval_weight = retrieval_weight
        self._lexical_weight = lexical_weight
        self._phrase_weight = phrase_weight

    @property
    def model_id(self) -> str | None:
        return self.MODEL_ID

    def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedChunk],
    ) -> RerankResult:
        started = time.perf_counter()
        scores: dict[UUID, float] = {}
        for chunk in candidates:
            scores[chunk.chunk_id] = (
                self._retrieval_weight * chunk.score
                + self._lexical_weight * token_overlap_score(query, chunk.content)
                + self._phrase_weight * phrase_match_score(query, chunk.content)
            )
        ordered = sorted(
            candidates,
            key=lambda chunk: (
                -scores[chunk.chunk_id],
                -chunk.score,
                str(chunk.document_id),
                chunk.chunk_index,
                str(chunk.chunk_id),
            ),
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return RerankResult(
            candidates=tuple(ordered),
            rerank_scores=scores,
            latency_ms=latency_ms,
            model_id=self.MODEL_ID,
        )


def merge_rerank_scores(
    primary: Mapping[UUID, float],
    remainder: Sequence[RetrievedChunk],
) -> dict[UUID, float]:
    """Rerank scores for the reranked window only; the remainder stays unscored."""
    merged = dict(primary)
    for chunk in remainder:
        merged.pop(chunk.chunk_id, None)
    return merged
