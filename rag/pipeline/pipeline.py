"""
Post-retrieval pipeline (spec 005-rag-pipeline/interface.md §1).

Stages: L4 re-validation -> [rerank] -> dedupe -> top-K -> context -> RagResult.

This component receives an already-authorized candidate list. It holds no
reference to the chunk store, the document store, or the embedding service, so
it structurally cannot query the global corpus or widen the caller's scope.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping, Sequence
from uuid import UUID

from rag.authorization.context import AuthorizationContext, require_authorization_context
from rag.contracts.retrieval import RetrievedChunk
from rag.ingestion.persian import normalize_persian
from rag.pipeline.config import PipelineConfig, validate_options
from rag.pipeline.context_builder import DelimitedContextBuilder
from rag.pipeline.deduplicator import ChunkDeduplicator
from rag.pipeline.provenance import (
    aggregate_sources,
    build_provenance,
    build_relevance,
    build_selected_chunks,
)
from rag.pipeline.reranker import (
    LexicalReranker,
    NoOpReranker,
    Reranker,
    merge_rerank_scores,
    select_rerank_window,
    validate_rerank_contract,
)
from rag.pipeline.selector import TopKSelector
from rag.pipeline.tokenizer import CharEstimateTokenCounter, TokenCounter
from rag.pipeline.types import (
    PipelineMetadata,
    PipelineOptions,
    RagResult,
    ResolvedIdentitySummary,
    RetrievalMetadata,
    SourceMetadata,
)
from rag.pipeline.validation import CandidateAuthorizationValidator


def query_hash(query: str) -> str:
    """SHA-256 of the fa-norm-v1 normalized query; the raw query is never echoed."""
    return hashlib.sha256(normalize_persian(query).encode("utf-8")).hexdigest()


def build_reranker(config: PipelineConfig) -> Reranker:
    """Reranker factory. No backend downloads or loads a model."""
    if config.backend == "lexical":
        return LexicalReranker(
            retrieval_weight=config.retrieval_weight,
            lexical_weight=config.lexical_weight,
            phrase_weight=config.phrase_weight,
        )
    return NoOpReranker()


class PostRetrievalPipeline:
    """Transforms authorized retrieval candidates into a structured RagResult."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        *,
        reranker: Reranker | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self._config = config or PipelineConfig()
        self._reranker = reranker or build_reranker(self._config)
        self._token_counter = token_counter or CharEstimateTokenCounter(
            self._config.chars_per_token
        )
        self._validator = CandidateAuthorizationValidator(
            strict=self._config.strict_authorization
        )
        self._deduplicator = ChunkDeduplicator()
        self._selector = TopKSelector()
        self._context_builder = DelimitedContextBuilder()

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @property
    def reranker(self) -> Reranker:
        return self._reranker

    def process(
        self,
        query: str,
        authorization_context: AuthorizationContext | None,
        candidates: Sequence[RetrievedChunk],
        retrieval: RetrievalMetadata,
        options: PipelineOptions | None = None,
        *,
        request_id: UUID | None = None,
        source_metadata: Mapping[UUID, SourceMetadata] | None = None,
    ) -> RagResult:
        authz = require_authorization_context(authorization_context)
        opts = options or self._config.to_options()
        validate_options(opts)

        started = time.perf_counter()
        stages: dict[str, int] = {}

        authorized, blocked = self._timed(
            stages,
            "authorization",
            lambda: self._validator.validate(candidates, authz),
        )

        reranked, rerank_scores, rerank_window_size = self._timed(
            stages,
            "rerank",
            lambda: self._rerank(query, list(authorized), opts),
        )

        deduped = self._timed(
            stages,
            "dedupe",
            lambda: self._deduplicator.deduplicate(
                reranked,
                by_content_hash=opts.dedupe_by_content_hash,
                rerank_scores=rerank_scores,
            ),
        )

        selection = self._timed(
            stages,
            "top_k",
            lambda: self._selector.select(
                deduped.chunks,
                top_k=opts.top_k,
                max_context_tokens=opts.max_context_tokens,
                token_counter=self._token_counter,
                rerank_scores=rerank_scores,
            ),
        )

        context = self._timed(
            stages,
            "context",
            lambda: self._context_builder.build(
                selection.selected,
                token_counter=self._token_counter,
                max_context_tokens=opts.max_context_tokens,
                context_format=opts.context_format,
            ),
        )

        latency_ms = int((time.perf_counter() - started) * 1000)
        dropped_duplicates = len(deduped.removed_duplicate_ids) + len(
            deduped.removed_near_duplicate_ids
        )
        return RagResult(
            request_id=request_id or authz.request_id,
            query_hash=query_hash(query),
            identity=self._identity_summary(authz),
            sources=aggregate_sources(selection.selected, source_metadata),
            chunks=build_selected_chunks(
                selection.selected,
                token_counter=self._token_counter,
                rerank_scores=rerank_scores,
            ),
            provenance=build_provenance(selection.selected, rerank_scores),
            relevance=build_relevance(
                authorized,
                selection.selected,
                candidate_count=retrieval.chunk_count,
                rerank_scores=rerank_scores,
            ),
            context=context,
            retrieval=retrieval,
            pipeline=PipelineMetadata(
                rerank_enabled=opts.rerank,
                rerank_model_id=self._reranker.model_id if opts.rerank else None,
                deduplicated_count=len(deduped.chunks),
                top_k_requested=opts.top_k,
                top_k_selected=len(selection.selected),
                dropped_duplicate_count=dropped_duplicates,
                dropped_token_budget_count=len(selection.dropped_for_token_budget),
                blocked_chunk_count=len(blocked),
                reranked_candidate_count=rerank_window_size,
                latency_ms=latency_ms,
                stages=stages,
            ),
        )

    def _rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        options: PipelineOptions,
    ) -> tuple[list[RetrievedChunk], dict[UUID, float], int]:
        if not options.rerank or not candidates:
            return candidates, {}, 0

        window, remainder = select_rerank_window(candidates, self._config.max_candidates)
        result = self._reranker.rerank(query, window)
        validate_rerank_contract(window, result)

        scores = merge_rerank_scores(result.rerank_scores, remainder)
        ordered = [*result.candidates, *remainder]
        if options.min_rerank_score is not None:
            ordered = [
                chunk
                for chunk in ordered
                if scores.get(chunk.chunk_id, chunk.score) >= options.min_rerank_score
            ]
        return ordered, scores, len(window)

    @staticmethod
    def _identity_summary(authz: AuthorizationContext) -> ResolvedIdentitySummary:
        return ResolvedIdentitySummary(
            user_id=authz.user_id,
            company_id=authz.company_id,
            department_ids=tuple(authz.allowed_department_ids),
        )

    @staticmethod
    def _timed(stages: dict[str, int], name: str, action):
        started = time.perf_counter()
        result = action()
        stages[name] = int((time.perf_counter() - started) * 1000)
        return result
