"""Authorized semantic candidate generation."""

from __future__ import annotations

from rag.embedding.types import Vector
from rag.retrieval.types import SemanticCandidate
from rag.storage.chunk_store import ChunkStore
from rag.storage.vector_search import VectorSearchScope


class CandidateGenerator:
    def __init__(self, chunk_store: ChunkStore) -> None:
        self._store = chunk_store

    def generate(
        self,
        query_vector: Vector,
        scope: VectorSearchScope,
        *,
        candidate_k: int,
        query_model_id: str,
        query_dimension: int,
    ) -> tuple[list[SemanticCandidate], int]:
        scored, pool_size = self._store.search(
            query_vector,
            scope,
            top_k=candidate_k,
            query_model_id=query_model_id,
            query_dimension=query_dimension,
        )
        candidates = [
            SemanticCandidate(
                chunk=item.chunk,
                semantic_score=item.score,
                rank_before=index + 1,
            )
            for index, item in enumerate(scored)
        ]
        return candidates, pool_size
