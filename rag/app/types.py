"""Public application/API types for retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievalApiRequest:
    query: str
    request_id: UUID
    top_k: int = 10


@dataclass(frozen=True, slots=True)
class RetrievalChunkResponse:
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    company_id: UUID
    department_id: UUID
    chunk_index: int


@dataclass(frozen=True, slots=True)
class RetrievalContextResponse:
    text: str
    char_count: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class RetrievalApiResponse:
    request_id: UUID
    chunks: tuple[RetrievalChunkResponse, ...]
    chunk_count: int
    latency_ms: int
    context: RetrievalContextResponse | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "request_id": str(self.request_id),
            "chunks": [
                {
                    "chunk_id": str(chunk.chunk_id),
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "score": chunk.score,
                    "metadata": {
                        "company_id": str(chunk.company_id),
                        "department_id": str(chunk.department_id),
                        "chunk_index": chunk.chunk_index,
                    },
                }
                for chunk in self.chunks
            ],
            "retrieval": {
                "chunk_count": self.chunk_count,
                "latency_ms": self.latency_ms,
            },
        }
        if self.context is not None:
            payload["context"] = {
                "text": self.context.text,
                "char_count": self.context.char_count,
                "truncated": self.context.truncated,
            }
        return payload
