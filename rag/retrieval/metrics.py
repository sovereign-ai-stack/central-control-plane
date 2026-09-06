"""Optional retrieval metrics collector."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalMetrics:
    query_embedding_latencies_ms: list[float] = field(default_factory=list)
    search_latencies_ms: list[float] = field(default_factory=list)
    candidate_counts: list[int] = field(default_factory=list)
    returned_counts: list[int] = field(default_factory=list)

    def record(
        self,
        *,
        query_embedding_latency_ms: float,
        search_latency_ms: float,
        candidate_count: int,
        returned_count: int,
    ) -> None:
        self.query_embedding_latencies_ms.append(query_embedding_latency_ms)
        self.search_latencies_ms.append(search_latency_ms)
        self.candidate_counts.append(candidate_count)
        self.returned_counts.append(returned_count)

    def clear(self) -> None:
        self.query_embedding_latencies_ms.clear()
        self.search_latencies_ms.clear()
        self.candidate_counts.clear()
        self.returned_counts.clear()
