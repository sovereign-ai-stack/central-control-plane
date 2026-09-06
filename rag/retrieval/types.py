"""Internal retrieval pipeline types."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag.ingestion.types import StoredChunk


@dataclass(frozen=True, slots=True)
class SemanticCandidate:
    chunk: StoredChunk
    semantic_score: float
    rank_before: int


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    chunk: StoredChunk
    semantic_score: float
    lexical_score: float
    phrase_match: float
    final_score: float
    rank_before: int
    rank_after: int


@dataclass(frozen=True, slots=True)
class ChunkDiagnostic:
    chunk_id: UUID
    document_id: UUID
    semantic_score: float
    lexical_score: float
    phrase_match: float
    final_score: float
    rank_before: int
    rank_after: int


@dataclass(frozen=True, slots=True)
class RetrievedContext:
    text: str
    char_count: int
    truncated: bool
    included_chunk_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class PipelineResult:
    chunks: tuple[RankedCandidate, ...]
    context: RetrievedContext
    diagnostics: tuple[ChunkDiagnostic, ...] | None = None
