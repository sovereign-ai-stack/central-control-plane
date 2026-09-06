"""Chunk index boundary — persisted chunks include embedding vectors."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from rag.ingestion.types import StoredChunk
from rag.storage.chunk_validation import validate_chunk, validate_chunk_batch
from rag.storage.vector_search import (
    ScoredChunk,
    VectorSearchScope,
    search_scoped_chunks,
)


@runtime_checkable
class ChunkStore(Protocol):
    """
    Chunk index with scoped vector search.

    Backend-agnostic: retrieval and ingestion depend only on this protocol,
    so a production vector database (Weaviate) substitutes for
    `InMemoryChunkStore` without changes elsewhere. Any implementation MUST
    apply `VectorSearchScope` inside the store query rather than filtering
    results afterwards. See specs/000-system-architecture/storage-extension.md.
    """

    def replace_document_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[StoredChunk],
    ) -> None:
        ...

    def delete_by_document_id(self, document_id: UUID) -> int:
        ...

    def count_by_document_id(self, document_id: UUID) -> int:
        ...

    def list_by_document_id(self, document_id: UUID) -> list[StoredChunk]:
        ...

    def search(
        self,
        query_vector,
        scope: VectorSearchScope,
        *,
        top_k: int,
        query_model_id: str,
        query_dimension: int,
    ) -> tuple[list[ScoredChunk], int]:
        ...

    def set_document_status(self, document_id: UUID, status: str) -> int:
        """
        Update the denormalised document status on a document's chunks.

        This is the searchability gate: only chunks marked ``indexed`` are
        returned when a scope carries no explicit document allow-list. Returns
        the number of chunks updated.
        """
        ...

    def ping(self) -> bool:
        """Cheap availability probe for the readiness endpoint."""
        ...


class InMemoryChunkStore:
    def __init__(self) -> None:
        self._chunks: dict[UUID, StoredChunk] = {}
        self._by_document: dict[UUID, set[UUID]] = {}
        self._fail_on_write: bool = False

    def set_document_status(self, document_id: UUID, status: str) -> int:
        from dataclasses import replace as _replace

        chunk_ids = self._by_document.get(document_id, set())
        for chunk_id in chunk_ids:
            existing = self._chunks.get(chunk_id)
            if existing is not None:
                self._chunks[chunk_id] = _replace(existing, document_status=status)
        return len(chunk_ids)

    def ping(self) -> bool:
        return True

    def set_fail_on_write(self, enabled: bool) -> None:
        self._fail_on_write = enabled

    def replace_document_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[StoredChunk],
    ) -> None:
        if self._fail_on_write:
            raise RuntimeError("simulated chunk store write failure")

        # Shared with every other backend so the write contract cannot drift.
        validate_chunk_batch(document_id, chunks)

        old_ids = set(self._by_document.get(document_id, set()))
        snapshot_chunks = dict(self._chunks)
        snapshot_docs = {k: set(v) for k, v in self._by_document.items()}
        new_ids: set[UUID] = set()
        try:
            for chunk in chunks:
                self._chunks[chunk.chunk_id] = chunk
                new_ids.add(chunk.chunk_id)
            self._by_document[document_id] = new_ids
            for stale_id in old_ids - new_ids:
                self._chunks.pop(stale_id, None)
        except Exception:
            self._chunks = snapshot_chunks
            self._by_document = snapshot_docs
            raise

    def delete_by_document_id(self, document_id: UUID) -> int:
        chunk_ids = self._by_document.pop(document_id, set())
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)
        return len(chunk_ids)

    def count_by_document_id(self, document_id: UUID) -> int:
        return len(self._by_document.get(document_id, set()))

    def list_by_document_id(self, document_id: UUID) -> list[StoredChunk]:
        ids = self._by_document.get(document_id, set())
        return [self._chunks[cid] for cid in sorted(ids, key=lambda x: self._chunks[x].chunk_index)]

    def search(
        self,
        query_vector,
        scope: VectorSearchScope,
        *,
        top_k: int,
        query_model_id: str,
        query_dimension: int,
    ) -> tuple[list[ScoredChunk], int]:
        return search_scoped_chunks(
            list(self._chunks.values()),
            query_vector,
            scope,
            top_k=top_k,
            query_model_id=query_model_id,
            query_dimension=query_dimension,
        )

    @staticmethod
    def _validate_chunk(chunk: StoredChunk) -> None:
        validate_chunk(chunk)
