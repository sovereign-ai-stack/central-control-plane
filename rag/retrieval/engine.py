"""Secure vector retrieval engine implementing SecureRetriever."""

from __future__ import annotations

import time

from rag.audit import AuditLog, emit_chunk_blocked, emit_retrieval_executed
from rag.authorization.context import AuthorizationContext, require_authorization_context
from rag.contracts.retrieval import (
    RetrievalOptions,
    RetrievalResult,
    RetrievedChunk,
    RetrievedContextSummary,
)
from rag.embedding.errors import EmbeddingError
from rag.embedding.service import EmbeddingService
from rag.ingestion.store.document_store import DocumentStore
from rag.pipeline.validation import CandidateAuthorizationValidator
from rag.retrieval.candidates import CandidateGenerator
from rag.retrieval.config import RetrievalConfig
from rag.retrieval.errors import RetrievalError
from rag.retrieval.metrics import RetrievalMetrics
from rag.retrieval.pipeline import RetrievalQualityPipeline
from rag.retrieval.types import RetrievedContext
from rag.storage.chunk_store import ChunkStore
from rag.storage.vector_search import VectorSearchScope


class SecureRetrievalEngine:
    """Authorization-first retrieval with semantic candidates and quality pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chunk_store: ChunkStore,
        document_store: DocumentStore,
        metrics: RetrievalMetrics | None = None,
        *,
        config: RetrievalConfig | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._embedding = embedding_service
        self._documents = document_store
        self._metrics = metrics
        self._config = config or RetrievalConfig()
        self._candidates = CandidateGenerator(chunk_store)
        self._pipeline = RetrievalQualityPipeline(self._config)
        self._audit = audit_log
        # Defense in depth: the store already filters server-side, but a
        # storage regression must not be able to leak a chunk through the
        # /retrieve path. /query has always had this; now both do.
        self._validator = CandidateAuthorizationValidator()

    def search(
        self,
        query: str,
        authorization_context: AuthorizationContext | None = None,
        options: RetrievalOptions | None = None,
        **kwargs: object,
    ) -> RetrievalResult:
        if kwargs:
            raise TypeError(
                "SecureRetriever.search() does not accept caller-supplied filter kwargs"
            )
        authz = require_authorization_context(authorization_context)
        opts = options or RetrievalOptions()
        final_k = opts.top_k
        candidate_k = opts.candidate_k or self._config.candidate_k
        self._config.validate_k(candidate_k=candidate_k, final_k=final_k)

        if not authz.has_department_access:
            return self._empty_result()

        try:
            embed_started = time.perf_counter()
            embed_result = self._embedding.embed_query(query)
            embed_ms = (time.perf_counter() - embed_started) * 1000
        except EmbeddingError as exc:
            raise RetrievalError("query embedding failed") from exc

        # allowed_document_ids=None -> the store filters on the denormalised
        # document status server-side. This replaces a full scan of every
        # document on every query, and removes the filter-size ceiling.
        scope = VectorSearchScope(
            company_id=authz.company_id,
            allowed_department_ids=authz.allowed_department_ids,
        )

        search_started = time.perf_counter()
        semantic_candidates, pool_size = self._candidates.generate(
            embed_result.vector,
            scope,
            candidate_k=candidate_k,
            query_model_id=embed_result.model_info.model_id,
            query_dimension=embed_result.model_info.dimension,
        )
        pipeline_result = self._pipeline.process(
            query,
            semantic_candidates,
            final_k=final_k,
            include_diagnostics=opts.include_diagnostics,
        )
        search_ms = (time.perf_counter() - search_started) * 1000

        if self._metrics is not None:
            self._metrics.record(
                query_embedding_latency_ms=embed_ms,
                search_latency_ms=search_ms,
                candidate_count=pool_size,
                returned_count=len(pipeline_result.chunks),
            )

        candidates = tuple(
            RetrievedChunk(
                chunk_id=item.chunk.chunk_id,
                document_id=item.chunk.document_id,
                company_id=item.chunk.company_id,
                department_id=item.chunk.department_id,
                content=item.chunk.content,
                score=item.final_score,
                chunk_index=item.chunk.chunk_index,
                document_version=item.chunk.document_version,
            )
            for item in pipeline_result.chunks
        )

        # L3 post-validation. Reaching a non-empty `blocked` set means the store
        # returned something outside the authorized scope, which is a critical
        # security signal, not a normal outcome.
        chunks, blocked = self._validator.validate(candidates, authz)
        if blocked and self._audit is not None:
            emit_chunk_blocked(
                self._audit,
                request_id=authz.request_id,
                user_id=authz.user_id,
                company_id=authz.company_id,
                blocked_chunk_ids=blocked,
                reason="post_validation_scope_mismatch",
            )

        if self._audit is not None:
            emit_retrieval_executed(
                self._audit,
                request_id=authz.request_id,
                user_id=authz.user_id,
                company_id=authz.company_id,
                department_count=len(authz.allowed_department_ids),
                query=query,
                candidate_count=pool_size,
                returned_count=len(chunks),
                chunk_ids=[chunk.chunk_id for chunk in chunks],
                latency_ms=embed_ms + search_ms,
            )

        context = (
            self._to_context_summary(pipeline_result.context)
            if not blocked
            # Context was assembled before validation, so if anything was
            # stripped the envelope may quote it. Rebuild empty rather than
            # risk returning unauthorized text.
            else RetrievedContextSummary(text="", char_count=0, truncated=False)
        )
        return RetrievalResult(chunks=chunks, context=context)

    @staticmethod
    def _empty_result() -> RetrievalResult:
        return RetrievalResult(
            chunks=(),
            context=RetrievedContextSummary(text="", char_count=0, truncated=False),
        )

    @staticmethod
    def _to_context_summary(context: RetrievedContext) -> RetrievedContextSummary:
        return RetrievedContextSummary(
            text=context.text,
            char_count=context.char_count,
            truncated=context.truncated,
        )

