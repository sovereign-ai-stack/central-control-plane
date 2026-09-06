"""Optional embedding metrics collector."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EmbeddingMetrics:
    query_latencies_ms: list[float] = field(default_factory=list)
    document_latencies_ms: list[float] = field(default_factory=list)
    document_batch_sizes: list[int] = field(default_factory=list)

    def record_query(self, latency_ms: float) -> None:
        self.query_latencies_ms.append(latency_ms)

    def record_documents(self, latency_ms: float, batch_size: int) -> None:
        self.document_latencies_ms.append(latency_ms)
        self.document_batch_sizes.append(batch_size)

    def clear(self) -> None:
        self.query_latencies_ms.clear()
        self.document_latencies_ms.clear()
        self.document_batch_sizes.clear()
