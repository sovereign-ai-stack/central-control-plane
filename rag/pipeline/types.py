"""
Post-retrieval RAG pipeline types (spec 005-rag-pipeline/interface.md).

These types carry the chunk metadata needed for citations. They never carry
embedding vectors: raw vectors stop at the storage/retrieval boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from rag.contracts.retrieval import RetrievedChunk

CONTEXT_FORMAT_DELIMITED_V1 = "delimited_v1"


@dataclass(frozen=True, slots=True)
class PipelineOptions:
    """Caller-tunable pipeline knobs. Contains no authorization scope fields."""

    rerank: bool = False
    top_k: int = 10
    max_context_tokens: int = 4096
    dedupe_by_content_hash: bool = True
    min_rerank_score: float | None = None
    context_format: str = CONTEXT_FORMAT_DELIMITED_V1


@dataclass(frozen=True, slots=True)
class RerankResult:
    candidates: tuple[RetrievedChunk, ...]
    rerank_scores: Mapping[UUID, float]
    latency_ms: int
    model_id: str | None


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    chunks: tuple[RetrievedChunk, ...]
    removed_duplicate_ids: tuple[UUID, ...]
    removed_near_duplicate_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class TopKResult:
    selected: tuple[RetrievedChunk, ...]
    dropped_for_top_k: tuple[UUID, ...]
    dropped_for_token_budget: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Server-side document metadata for citations (never caller-supplied)."""

    title: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedIdentitySummary:
    user_id: UUID
    company_id: UUID
    department_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class RetrievedSource:
    document_id: UUID
    department_id: UUID
    chunk_ids: tuple[UUID, ...]
    chunk_count: int
    max_score: float
    title: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class SelectedChunk:
    chunk_id: UUID
    document_id: UUID
    company_id: UUID
    department_id: UUID
    chunk_index: int
    content: str
    retrieval_score: float
    token_count: int
    rerank_score: float | None = None
    content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    citation_id: str
    document_id: UUID
    chunk_id: UUID
    chunk_index: int
    retrieval_score: float
    position_in_context: int
    rerank_score: float | None = None


@dataclass(frozen=True, slots=True)
class RelevanceSummary:
    candidate_count: int
    selected_count: int
    top_retrieval_score: float | None = None
    top_rerank_score: float | None = None
    mean_retrieval_score: float | None = None


@dataclass(frozen=True, slots=True)
class AssembledContext:
    """Delimited untrusted data blocks. Never system instructions."""

    text: str
    token_count: int
    format: str
    block_count: int


@dataclass(frozen=True, slots=True)
class AppliedFilter:
    company_id: UUID
    department_count: int


@dataclass(frozen=True, slots=True)
class RetrievalMetadata:
    """Stats handed to the pipeline by the orchestrator; department IDs not expanded."""

    chunk_count: int
    latency_ms: int
    filter_applied: AppliedFilter


@dataclass(frozen=True, slots=True)
class PipelineMetadata:
    rerank_enabled: bool
    deduplicated_count: int
    top_k_requested: int
    top_k_selected: int
    dropped_duplicate_count: int
    dropped_token_budget_count: int
    latency_ms: int
    rerank_model_id: str | None = None
    blocked_chunk_count: int = 0
    reranked_candidate_count: int = 0
    stages: Mapping[str, int] | None = None


@dataclass(frozen=True, slots=True)
class RagResult:
    """
    Structured output for the downstream vLLM Gateway.

    Deliberately has no `answer`, `system_prompt`, `messages`, or
    `authorization_instructions` field (interface.md §8).
    """

    request_id: UUID
    query_hash: str
    identity: ResolvedIdentitySummary
    sources: tuple[RetrievedSource, ...]
    chunks: tuple[SelectedChunk, ...]
    provenance: tuple[ProvenanceRecord, ...]
    relevance: RelevanceSummary
    context: AssembledContext
    retrieval: RetrievalMetadata
    pipeline: PipelineMetadata
