"""Shared retrieval evaluation helpers for benchmark and diagnostics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from benchmarks.persian.dataset import BenchmarkDataset, query_category
from benchmarks.persian.metrics import (
    QueryMetrics,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rag.embedding.service import EmbeddingService


@dataclass(frozen=True, slots=True)
class RankedHit:
    doc_id: str
    score: float
    text: str


@dataclass(frozen=True, slots=True)
class QueryRetrievalReport:
    query_id: str
    query_text: str
    category: str
    expected_doc_ids: tuple[str, ...]
    top_hits: tuple[RankedHit, ...]
    expected_ranks: dict[str, int]
    expected_scores: dict[str, float]


def encode_corpus(service: EmbeddingService, dataset: BenchmarkDataset):
    doc_ids = [doc.doc_id for doc in dataset.corpus]
    texts = [doc.text for doc in dataset.corpus]
    doc_result = service.embed_documents(texts)
    doc_matrix = np.vstack(doc_result.vectors) if doc_result.vectors else np.empty((0, 0))
    corpus_text = {doc.doc_id: doc.text for doc in dataset.corpus}
    return doc_ids, doc_matrix, corpus_text


def rank_query(
    service: EmbeddingService,
    query_text: str,
    doc_ids: Sequence[str],
    doc_matrix: np.ndarray,
    corpus_text: dict[str, str],
    *,
    top_k: int = 5,
) -> tuple[list[str], list[RankedHit]]:
    query_vector = service.embed_query(query_text).vector
    scores = doc_matrix @ query_vector
    order = np.argsort(-scores)
    ranked_ids = [doc_ids[i] for i in order]
    hits = [
        RankedHit(doc_id=doc_ids[i], score=float(scores[i]), text=corpus_text[doc_ids[i]])
        for i in order[:top_k]
    ]
    return ranked_ids, hits


def build_query_metrics(
    query_id: str,
    category: str,
    relevant_doc_ids: tuple[str, ...],
    ranked_ids: list[str],
    *,
    k_values: list[int],
    ndcg_k_values: list[int],
) -> QueryMetrics:
    relevant = set(relevant_doc_ids)
    row = QueryMetrics(
        query_id=query_id,
        category=category,
        reciprocal_rank=reciprocal_rank(relevant, ranked_ids),
    )
    for k in k_values:
        row.recall_at_k[k] = recall_at_k(relevant, ranked_ids, k)
    for k in (5, 10):
        if k in k_values or k in ndcg_k_values:
            row.precision_at_k[k] = precision_at_k(relevant, ranked_ids, k)
    for k in ndcg_k_values:
        row.ndcg_at_k[k] = ndcg_at_k(relevant, ranked_ids, k)
    return row


def debug_query_report(
    service: EmbeddingService,
    dataset: BenchmarkDataset,
    query_id: str,
    *,
    doc_ids: Sequence[str] | None = None,
    doc_matrix: np.ndarray | None = None,
    corpus_text: dict[str, str] | None = None,
    top_k: int = 5,
) -> QueryRetrievalReport:
    if doc_ids is None or doc_matrix is None or corpus_text is None:
        doc_ids, doc_matrix, corpus_text = encode_corpus(service, dataset)

    query = next(item for item in dataset.queries if item.query_id == query_id)
    ranked_ids, hits = rank_query(
        service, query.text, doc_ids, doc_matrix, corpus_text, top_k=top_k
    )
    query_vector = service.embed_query(query.text).vector
    scores = doc_matrix @ query_vector
    id_to_index = {doc_id: index for index, doc_id in enumerate(doc_ids)}
    expected_ranks = {
        doc_id: ranked_ids.index(doc_id) + 1 for doc_id in query.relevant_doc_ids if doc_id in ranked_ids
    }
    expected_scores = {
        doc_id: float(scores[id_to_index[doc_id]])
        for doc_id in query.relevant_doc_ids
        if doc_id in id_to_index
    }
    return QueryRetrievalReport(
        query_id=query.query_id,
        query_text=query.text,
        category=query_category(query),
        expected_doc_ids=query.relevant_doc_ids,
        top_hits=tuple(hits),
        expected_ranks=expected_ranks,
        expected_scores=expected_scores,
    )
