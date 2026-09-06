"""
Citation provenance and document-level source aggregation (spec 005 §6.2, §6.4).

Provenance is what makes retrieved content citable downstream: every context
block maps 1:1 to a record carrying `citation_id`, `document_id`, `chunk_id`,
`chunk_index`, scores, and the block's position in the context.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from rag.contracts.retrieval import RetrievedChunk
from rag.pipeline.context_builder import citation_id
from rag.pipeline.deduplicator import normalized_content_hash
from rag.pipeline.tokenizer import TokenCounter
from rag.pipeline.types import (
    ProvenanceRecord,
    RelevanceSummary,
    RetrievedSource,
    SelectedChunk,
    SourceMetadata,
)


def build_provenance(
    selected: Sequence[RetrievedChunk],
    rerank_scores: Mapping[UUID, float] | None = None,
) -> tuple[ProvenanceRecord, ...]:
    scores = rerank_scores or {}
    return tuple(
        ProvenanceRecord(
            citation_id=citation_id(position),
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            retrieval_score=chunk.score,
            rerank_score=scores.get(chunk.chunk_id),
            position_in_context=position,
        )
        for position, chunk in enumerate(selected)
    )


def build_selected_chunks(
    selected: Sequence[RetrievedChunk],
    *,
    token_counter: TokenCounter,
    rerank_scores: Mapping[UUID, float] | None = None,
) -> tuple[SelectedChunk, ...]:
    scores = rerank_scores or {}
    return tuple(
        SelectedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            company_id=chunk.company_id,
            department_id=chunk.department_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            retrieval_score=chunk.score,
            rerank_score=scores.get(chunk.chunk_id),
            content_hash=normalized_content_hash(chunk.content),
            token_count=token_counter.count(chunk.content),
        )
        for chunk in selected
    )


def aggregate_sources(
    selected: Sequence[RetrievedChunk],
    source_metadata: Mapping[UUID, SourceMetadata] | None = None,
) -> tuple[RetrievedSource, ...]:
    """
    Roll selected chunks up by document, preserving first-seen chunk order.

    `source_metadata` is server-side document metadata keyed by document_id and
    is only ever read for documents already present in the selected set.
    """
    metadata = source_metadata or {}
    order: list[UUID] = []
    grouped: dict[UUID, list[RetrievedChunk]] = {}
    for chunk in selected:
        if chunk.document_id not in grouped:
            grouped[chunk.document_id] = []
            order.append(chunk.document_id)
        grouped[chunk.document_id].append(chunk)

    sources: list[RetrievedSource] = []
    for document_id in order:
        chunks = grouped[document_id]
        document_metadata = metadata.get(document_id, SourceMetadata())
        sources.append(
            RetrievedSource(
                document_id=document_id,
                department_id=chunks[0].department_id,
                chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
                chunk_count=len(chunks),
                max_score=max(chunk.score for chunk in chunks),
                title=document_metadata.title,
                source=document_metadata.source,
            )
        )
    return tuple(sources)


def build_relevance(
    candidates: Sequence[RetrievedChunk],
    selected: Sequence[RetrievedChunk],
    *,
    candidate_count: int,
    rerank_scores: Mapping[UUID, float] | None = None,
) -> RelevanceSummary:
    scores = rerank_scores or {}
    retrieval_scores = [chunk.score for chunk in candidates]
    selected_rerank = [
        scores[chunk.chunk_id] for chunk in selected if chunk.chunk_id in scores
    ]
    return RelevanceSummary(
        candidate_count=candidate_count,
        selected_count=len(selected),
        top_retrieval_score=max(retrieval_scores) if retrieval_scores else None,
        top_rerank_score=max(selected_rerank) if selected_rerank else None,
        mean_retrieval_score=(
            sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else None
        ),
    )
