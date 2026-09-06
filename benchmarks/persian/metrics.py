"""Retrieval metric calculations for Persian embedding benchmark."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field


def recall_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = ranked[:k]
    return 1.0 if any(doc_id in relevant for doc_id in top) else 0.0


def precision_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    if k == 0:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for doc_id in top if doc_id in relevant)
    return hits / k


def reciprocal_rank(relevant: set[str], ranked: list[str]) -> float:
    for index, doc_id in enumerate(ranked, start=1):
        if doc_id in relevant:
            return 1.0 / index
    return 0.0


def dcg_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    score = 0.0
    for index, doc_id in enumerate(ranked[:k], start=1):
        if doc_id in relevant:
            score += 1.0 / math.log2(index + 1)
    return score


def ndcg_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    dcg = dcg_at_k(relevant, ranked, k)
    ideal_hits = min(len(relevant), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def cosine_rank(
    query_vector,
    doc_ids: list[str],
    doc_matrix,
) -> list[str]:
    import numpy as np

    if doc_matrix.size == 0:
        return []
    scores = doc_matrix @ query_vector
    order = np.argsort(-scores)
    return [doc_ids[i] for i in order]


@dataclass
class QueryMetrics:
    query_id: str
    category: str
    recall_at_k: dict[int, float] = field(default_factory=dict)
    precision_at_k: dict[int, float] = field(default_factory=dict)
    reciprocal_rank: float = 0.0
    ndcg_at_k: dict[int, float] = field(default_factory=dict)


@dataclass
class AggregateMetrics:
    recall_at_k: dict[int, float] = field(default_factory=dict)
    precision_at_k: dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    ndcg_at_k: dict[int, float] = field(default_factory=dict)
    by_category: dict[str, dict[str, float]] = field(default_factory=dict)


def aggregate_query_metrics(
    per_query: Iterable[QueryMetrics],
    *,
    k_values: list[int],
    ndcg_k_values: list[int],
) -> AggregateMetrics:
    rows = list(per_query)
    if not rows:
        return AggregateMetrics()

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    aggregate = AggregateMetrics(
        recall_at_k={k: mean([row.recall_at_k[k] for row in rows]) for k in k_values},
        precision_at_k={
            k: mean([row.precision_at_k[k] for row in rows if k in row.precision_at_k])
            for k in sorted({k for row in rows for k in row.precision_at_k})
        },
        mrr=mean([row.reciprocal_rank for row in rows]),
        ndcg_at_k={k: mean([row.ndcg_at_k[k] for row in rows]) for k in ndcg_k_values},
    )

    categories = sorted({row.category for row in rows})
    for category in categories:
        subset = [row for row in rows if row.category == category]
        aggregate.by_category[category] = {
            "recall_at_5": mean([row.recall_at_k.get(5, 0.0) for row in subset]),
            "mrr": mean([row.reciprocal_rank for row in subset]),
        }
        if category in {"semantic", "paraphrase", "mixed_language", "technical", "short_query", "long_query"}:
            for k in (1, 3, 5, 10):
                aggregate.by_category[category][f"recall_at_{k}"] = mean(
                    [row.recall_at_k.get(k, 0.0) for row in subset]
                )
            for k in ndcg_k_values:
                aggregate.by_category[category][f"ndcg_at_{k}"] = mean(
                    [row.ndcg_at_k.get(k, 0.0) for row in subset]
                )
    return aggregate
