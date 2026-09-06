"""
RAG orchestrator: secure retrieval (004) -> post-retrieval pipeline (005).

This is the composition root that owns the retrieval boundary. It is the only
component in this package permitted to touch stores, and it does so exclusively
through the secure retrieval service, whose scope is derived from the resolved
`AuthorizationContext`.

Document metadata for citations is looked up **only** for document IDs that
already appear in the authorized candidate set, and each record is re-checked
against the authorization context before use, so the lookup can never introduce
a document the caller was not already permitted to see.
"""

from __future__ import annotations

import time
from uuid import UUID

from rag.authorization.context import AuthorizationContext
from rag.contracts.retrieval import RetrievalOptions, RetrievalResult, RetrievedChunk
from rag.identity.types import TrustedIdentityPayload
from rag.ingestion.store.document_store import DocumentStore
from rag.pipeline.config import PipelineConfig
from rag.pipeline.pipeline import PostRetrievalPipeline
from rag.pipeline.types import (
    AppliedFilter,
    PipelineOptions,
    RagResult,
    RetrievalMetadata,
    SourceMetadata,
)
from rag.retrieval.config import MAX_CANDIDATE_K, MAX_FINAL_K
from rag.retrieval.service import RetrievalService


class RagOrchestrator:
    """Executes the full retrieve -> rerank -> assemble path for one request."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        pipeline: PostRetrievalPipeline,
        *,
        config: PipelineConfig | None = None,
        document_store: DocumentStore | None = None,
    ) -> None:
        self._retrieval = retrieval_service
        self._pipeline = pipeline
        self._config = config or pipeline.config
        self._documents = document_store

    @property
    def config(self) -> PipelineConfig:
        return self._config

    def execute(
        self,
        query: str,
        request_id: UUID,
        bearer_token: str | None = None,
        *,
        trusted_identity: TrustedIdentityPayload | None = None,
        options: PipelineOptions | None = None,
    ) -> RagResult:
        opts = options or self._config.to_options()
        candidate_pool_k = self._candidate_pool_k(opts.top_k)

        started = time.perf_counter()
        authz, retrieval = self._retrieval.search_with_context(
            query,
            request_id,
            bearer_token,
            trusted_identity=trusted_identity,
            options=RetrievalOptions(
                top_k=candidate_pool_k,
                candidate_k=self._candidate_k(candidate_pool_k),
            ),
        )
        retrieval_latency_ms = int((time.perf_counter() - started) * 1000)

        candidates = self._authorized_chunks(retrieval)
        return self._pipeline.process(
            query,
            authz,
            candidates,
            RetrievalMetadata(
                chunk_count=len(candidates),
                latency_ms=retrieval_latency_ms,
                filter_applied=AppliedFilter(
                    company_id=authz.company_id,
                    department_count=len(authz.allowed_department_ids),
                ),
            ),
            opts,
            request_id=request_id,
            source_metadata=self._source_metadata(candidates, authz),
        )

    def _candidate_pool_k(self, top_k: int) -> int:
        """Retrieve a pool at least as large as top_k so reranking has room to work."""
        return min(max(top_k, self._config.candidate_pool_k), MAX_FINAL_K)

    @staticmethod
    def _candidate_k(candidate_pool_k: int) -> int:
        return min(max(candidate_pool_k, 1), MAX_CANDIDATE_K)

    @staticmethod
    def _authorized_chunks(result: RetrievalResult) -> tuple[RetrievedChunk, ...]:
        return tuple(
            chunk for chunk in result.chunks if isinstance(chunk, RetrievedChunk)
        )

    def _source_metadata(
        self,
        candidates: tuple[RetrievedChunk, ...],
        authz: AuthorizationContext,
    ) -> dict[UUID, SourceMetadata]:
        if self._documents is None:
            return {}
        allowed_departments = set(authz.allowed_department_ids)
        metadata: dict[UUID, SourceMetadata] = {}
        for document_id in {chunk.document_id for chunk in candidates}:
            record = self._documents.get(document_id)
            if record is None:
                continue
            if record.company_id != authz.company_id:
                continue
            if record.department_id not in allowed_departments:
                continue
            metadata[document_id] = SourceMetadata(
                title=record.title,
                source=record.source,
            )
        return metadata
