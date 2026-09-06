"""Collapse exact duplicate normalized chunk content."""

from __future__ import annotations

from rag.ingestion.persian import normalize_persian
from rag.retrieval.types import RankedCandidate


class Deduplicator:
    def deduplicate(self, ranked: list[RankedCandidate]) -> list[RankedCandidate]:
        seen: set[str] = set()
        unique: list[RankedCandidate] = []
        for candidate in ranked:
            key = normalize_persian(candidate.chunk.content)
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique
