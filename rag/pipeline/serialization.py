"""
RagResult JSON serialization (spec 005-rag-pipeline/contracts/rag-result.yaml).

The emitted payload contains no embedding vectors, no raw query text, no
`answer`, no `system_prompt`, and no chat `messages` array.
"""

from __future__ import annotations

from rag.pipeline.types import (
    AssembledContext,
    PipelineMetadata,
    ProvenanceRecord,
    RagResult,
    RelevanceSummary,
    RetrievalMetadata,
    RetrievedSource,
    SelectedChunk,
)


def rag_result_to_dict(result: RagResult) -> dict[str, object]:
    return {
        "request_id": str(result.request_id),
        "query_hash": result.query_hash,
        "identity": {
            "user_id": str(result.identity.user_id),
            "company_id": str(result.identity.company_id),
            "department_ids": [
                str(department_id) for department_id in result.identity.department_ids
            ],
        },
        "sources": [_source_to_dict(source) for source in result.sources],
        "chunks": [_chunk_to_dict(chunk) for chunk in result.chunks],
        "provenance": [_provenance_to_dict(record) for record in result.provenance],
        "relevance": _relevance_to_dict(result.relevance),
        "context": _context_to_dict(result.context),
        "retrieval": _retrieval_to_dict(result.retrieval),
        "pipeline": _pipeline_to_dict(result.pipeline),
    }


def _source_to_dict(source: RetrievedSource) -> dict[str, object]:
    return {
        "document_id": str(source.document_id),
        "department_id": str(source.department_id),
        "chunk_ids": [str(chunk_id) for chunk_id in source.chunk_ids],
        "chunk_count": source.chunk_count,
        "max_score": source.max_score,
        "title": source.title,
        "source": source.source,
    }


def _chunk_to_dict(chunk: SelectedChunk) -> dict[str, object]:
    return {
        "chunk_id": str(chunk.chunk_id),
        "document_id": str(chunk.document_id),
        "company_id": str(chunk.company_id),
        "department_id": str(chunk.department_id),
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "retrieval_score": chunk.retrieval_score,
        "rerank_score": chunk.rerank_score,
        "content_hash": chunk.content_hash,
        "token_count": chunk.token_count,
    }


def _provenance_to_dict(record: ProvenanceRecord) -> dict[str, object]:
    return {
        "citation_id": record.citation_id,
        "document_id": str(record.document_id),
        "chunk_id": str(record.chunk_id),
        "chunk_index": record.chunk_index,
        "retrieval_score": record.retrieval_score,
        "rerank_score": record.rerank_score,
        "position_in_context": record.position_in_context,
    }


def _relevance_to_dict(relevance: RelevanceSummary) -> dict[str, object]:
    return {
        "top_retrieval_score": relevance.top_retrieval_score,
        "top_rerank_score": relevance.top_rerank_score,
        "mean_retrieval_score": relevance.mean_retrieval_score,
        "candidate_count": relevance.candidate_count,
        "selected_count": relevance.selected_count,
    }


def _context_to_dict(context: AssembledContext) -> dict[str, object]:
    return {
        "text": context.text,
        "token_count": context.token_count,
        "format": context.format,
        "block_count": context.block_count,
    }


def _retrieval_to_dict(retrieval: RetrievalMetadata) -> dict[str, object]:
    return {
        "chunk_count": retrieval.chunk_count,
        "latency_ms": retrieval.latency_ms,
        "filter_applied": {
            "company_id": str(retrieval.filter_applied.company_id),
            "department_count": retrieval.filter_applied.department_count,
        },
    }


def _pipeline_to_dict(metadata: PipelineMetadata) -> dict[str, object]:
    return {
        "rerank_enabled": metadata.rerank_enabled,
        "rerank_model_id": metadata.rerank_model_id,
        "deduplicated_count": metadata.deduplicated_count,
        "top_k_requested": metadata.top_k_requested,
        "top_k_selected": metadata.top_k_selected,
        "dropped_duplicate_count": metadata.dropped_duplicate_count,
        "dropped_token_budget_count": metadata.dropped_token_budget_count,
        "blocked_chunk_count": metadata.blocked_chunk_count,
        "reranked_candidate_count": metadata.reranked_candidate_count,
        "latency_ms": metadata.latency_ms,
        "stages": dict(metadata.stages) if metadata.stages is not None else {},
    }
