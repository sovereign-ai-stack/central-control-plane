"""
Chunk deduplication over authorized candidates (spec 005-rag-pipeline/interface.md §3).

Rules:

- same `chunk_id` -> keep the highest-scoring instance
- same normalized `content_hash` -> keep the highest-scoring instance
- order among survivors preserves the incoming rerank/retrieval order
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from rag.contracts.retrieval import RetrievedChunk
from rag.ingestion.persian import normalize_persian
from rag.ingestion.validation import chunk_content_hash
from rag.pipeline.types import DeduplicationResult


def normalized_content_hash(content: str) -> str:
    """fa-norm-v1 normalized SHA-256, matching the ingestion chunk hash."""
    return chunk_content_hash(normalize_persian(content))


class ChunkDeduplicator:
    def deduplicate(
        self,
        candidates: Sequence[RetrievedChunk],
        *,
        by_chunk_id: bool = True,
        by_content_hash: bool = True,
        rerank_scores: Mapping[UUID, float] | None = None,
    ) -> DeduplicationResult:
        scores = rerank_scores or {}

        def effective_score(chunk: RetrievedChunk) -> float:
            return scores.get(chunk.chunk_id, chunk.score)

        def wins(position: int, incumbent: int | None) -> bool:
            """First occurrence wins ties, so equal scores keep the earlier chunk."""
            if incumbent is None:
                return True
            return effective_score(candidates[position]) > effective_score(
                candidates[incumbent]
            )

        keep_by_id: dict[UUID, int] = {}
        keep_by_hash: dict[str, int] = {}
        duplicate_ids: list[UUID] = []
        near_duplicate_ids: list[UUID] = []

        if by_chunk_id:
            for position, chunk in enumerate(candidates):
                if wins(position, keep_by_id.get(chunk.chunk_id)):
                    keep_by_id[chunk.chunk_id] = position

        id_survivors = (
            sorted(keep_by_id.values())
            if by_chunk_id
            else list(range(len(candidates)))
        )
        id_survivor_set = set(id_survivors)
        for position, chunk in enumerate(candidates):
            if position not in id_survivor_set:
                duplicate_ids.append(chunk.chunk_id)

        if by_content_hash:
            for position in id_survivors:
                key = normalized_content_hash(candidates[position].content)
                if wins(position, keep_by_hash.get(key)):
                    keep_by_hash[key] = position
            final_positions = sorted(keep_by_hash.values())
            final_set = set(final_positions)
            for position in id_survivors:
                if position not in final_set:
                    near_duplicate_ids.append(candidates[position].chunk_id)
        else:
            final_positions = id_survivors

        return DeduplicationResult(
            chunks=tuple(candidates[position] for position in final_positions),
            removed_duplicate_ids=tuple(duplicate_ids),
            removed_near_duplicate_ids=tuple(near_duplicate_ids),
        )
