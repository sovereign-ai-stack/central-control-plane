"""Optional per-document chunk cap after reranking."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from rag.retrieval.types import RankedCandidate


class DiversityFilter:
    def apply(
        self,
        ranked: list[RankedCandidate],
        *,
        max_chunks_per_document: int | None,
    ) -> list[RankedCandidate]:
        if max_chunks_per_document is None:
            return ranked
        counts: defaultdict[UUID, int] = defaultdict(int)
        filtered: list[RankedCandidate] = []
        for candidate in ranked:
            doc_id = candidate.chunk.document_id
            if counts[doc_id] >= max_chunks_per_document:
                continue
            counts[doc_id] += 1
            filtered.append(candidate)
        return filtered
