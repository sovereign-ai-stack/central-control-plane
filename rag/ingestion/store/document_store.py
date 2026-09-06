"""
Document metadata store.

Mirrors the `ChunkStore` arrangement: a protocol that callers depend on, an
in-memory implementation for tests and local runs, and a durable implementation
for production (`sqlite_document_store.py`).

This store is security-relevant, not just bookkeeping: `SecureRetrievalEngine`
uses document status and scope to decide what is searchable, so an
implementation that loses state silently makes indexed content unreachable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from rag.ingestion.types import DocumentRecord, DocumentStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


@runtime_checkable
class DocumentStore(Protocol):
    """Document metadata index. Backend-agnostic."""

    def count(self) -> int:
        ...

    def list_all(self) -> list[DocumentRecord]:
        ...

    def create_processing(
        self,
        *,
        company_id: UUID,
        department_id: UUID,
        source: str,
        language: str,
        source_type: str,
        content_hash: str,
        normalization_version: str,
        document_id: UUID | None = None,
        title: str | None = None,
        source_uri: str | None = None,
    ) -> DocumentRecord:
        ...

    def get(self, document_id: UUID) -> DocumentRecord | None:
        ...

    def find_indexed_by_content_hash(
        self,
        company_id: UUID,
        department_id: UUID,
        content_hash: str,
    ) -> DocumentRecord | None:
        ...

    def mark_indexed(
        self,
        document_id: UUID,
        *,
        chunk_count: int,
        content_hash: str,
        version: int | None = None,
    ) -> DocumentRecord:
        ...

    def mark_failed(self, document_id: UUID, reason: str) -> DocumentRecord:
        ...

    def mark_deleted(self, document_id: UUID) -> DocumentRecord:
        ...

    def begin_reindex(self, document_id: UUID, content_hash: str) -> DocumentRecord:
        ...

    def list_indexed_ids(
        self,
        company_id: UUID,
        department_ids: tuple[UUID, ...],
    ) -> frozenset[UUID]:
        """
        Indexed document ids within a company/department scope.

        Retained for reconciliation and for callers that still want an explicit
        document allow-list; retrieval no longer calls it per query.
        """
        ...

    def ping(self) -> bool:
        """Cheap availability probe for the readiness endpoint."""
        ...


class InMemoryDocumentStore:
    """Process-local document store. State does not survive a restart."""

    def __init__(self) -> None:
        self._documents: dict[UUID, DocumentRecord] = {}

    def count(self) -> int:
        return len(self._documents)

    def list_all(self) -> list[DocumentRecord]:
        return list(self._documents.values())

    def create_processing(
        self,
        *,
        company_id: UUID,
        department_id: UUID,
        source: str,
        language: str,
        source_type: str,
        content_hash: str,
        normalization_version: str,
        document_id: UUID | None = None,
        title: str | None = None,
        source_uri: str | None = None,
    ) -> DocumentRecord:
        now = utc_now()
        doc_id = document_id or uuid4()
        if doc_id in self._documents:
            existing = self._documents[doc_id]
            if existing.status != DocumentStatus.DELETED:
                raise ValueError("document_id already exists")
        record = DocumentRecord(
            id=doc_id,
            company_id=company_id,
            department_id=department_id,
            title=title,
            source=source,
            language=language,
            source_type=source_type,
            source_uri=source_uri,
            version=1,
            status=DocumentStatus.PROCESSING,
            content_hash=content_hash,
            normalization_version=normalization_version,
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        self._documents[doc_id] = record
        return record

    def get(self, document_id: UUID) -> DocumentRecord | None:
        return self._documents.get(document_id)

    def find_indexed_by_content_hash(
        self,
        company_id: UUID,
        department_id: UUID,
        content_hash: str,
    ) -> DocumentRecord | None:
        for document in self._documents.values():
            if (
                document.status == DocumentStatus.INDEXED
                and document.company_id == company_id
                and document.department_id == department_id
                and document.content_hash == content_hash
            ):
                return document
        return None

    def mark_indexed(
        self,
        document_id: UUID,
        *,
        chunk_count: int,
        content_hash: str,
        version: int | None = None,
    ) -> DocumentRecord:
        document = self._require(document_id)
        document.status = DocumentStatus.INDEXED
        document.chunk_count = chunk_count
        document.content_hash = content_hash
        document.updated_at = utc_now()
        document.indexed_at = document.updated_at
        document.failed_at = None
        document.failure_reason = None
        if version is not None:
            document.version = version
        return document

    def mark_failed(self, document_id: UUID, reason: str) -> DocumentRecord:
        document = self._require(document_id)
        document.status = DocumentStatus.FAILED
        document.chunk_count = 0
        document.failed_at = utc_now()
        document.failure_reason = reason
        document.updated_at = document.failed_at
        return document

    def mark_deleted(self, document_id: UUID) -> DocumentRecord:
        document = self._require(document_id)
        document.status = DocumentStatus.DELETED
        document.chunk_count = 0
        document.updated_at = utc_now()
        return document

    def begin_reindex(self, document_id: UUID, content_hash: str) -> DocumentRecord:
        document = self._require(document_id)
        document.status = DocumentStatus.PROCESSING
        document.content_hash = content_hash
        document.updated_at = utc_now()
        return document

    def list_indexed_ids(
        self,
        company_id: UUID,
        department_ids: tuple[UUID, ...],
    ) -> frozenset[UUID]:
        allowed = set(department_ids)
        return frozenset(
            document.id
            for document in self._documents.values()
            if document.status == DocumentStatus.INDEXED
            and document.company_id == company_id
            and document.department_id in allowed
        )

    def ping(self) -> bool:
        return True

    def _require(self, document_id: UUID) -> DocumentRecord:
        document = self.get(document_id)
        if document is None:
            raise KeyError(f"document not found: {document_id}")
        return document
