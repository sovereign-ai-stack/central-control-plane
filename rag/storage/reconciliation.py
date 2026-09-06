"""
Reconciliation between the document store and the vector store.

Two failure modes this detects, both introduced by having durable state in two
systems with no shared transaction:

1. **Drift** — a document's recorded status disagrees with the denormalised
   `document_status` on its chunks. Searchability is decided by the chunk field,
   so drift means content is either wrongly hidden or wrongly visible. The
   second direction is a security concern, so it is reported separately.

2. **Orphans** — chunks whose document has no record at all. Before the document
   store was durable these accumulated invisibly on every restart, unreachable
   and impossible to delete through the service.

This module only *reports* by default. Repair is an explicit, separate call, so
an operator decides rather than a background job silently deleting data.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from rag.ingestion.store.document_store import DocumentStore
from rag.ingestion.types import DocumentStatus
from rag.storage.chunk_store import ChunkStore

logger = logging.getLogger(__name__)

SEARCHABLE = DocumentStatus.INDEXED.value


@dataclass(frozen=True, slots=True)
class DocumentDrift:
    document_id: UUID
    document_status: str
    chunk_status: str | None
    chunk_count: int

    @property
    def is_over_exposed(self) -> bool:
        """
        Chunks are searchable but the document says they should not be.

        The security-relevant direction: content reachable that a delete,
        failure, or reindex should have hidden.
        """
        return self.chunk_status == SEARCHABLE and self.document_status != SEARCHABLE


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    checked_documents: int = 0
    drifted: tuple[DocumentDrift, ...] = field(default_factory=tuple)
    orphaned_document_ids: tuple[UUID, ...] = field(default_factory=tuple)

    @property
    def over_exposed(self) -> tuple[DocumentDrift, ...]:
        return tuple(item for item in self.drifted if item.is_over_exposed)

    @property
    def is_clean(self) -> bool:
        return not self.drifted and not self.orphaned_document_ids

    def to_dict(self) -> dict[str, object]:
        return {
            "checked_documents": self.checked_documents,
            "drift_count": len(self.drifted),
            "over_exposed_count": len(self.over_exposed),
            "orphaned_count": len(self.orphaned_document_ids),
            "clean": self.is_clean,
        }


class StoreReconciler:
    """Compares document records against the chunks that represent them."""

    def __init__(
        self,
        document_store: DocumentStore,
        chunk_store: ChunkStore,
    ) -> None:
        self._documents = document_store
        self._chunks = chunk_store

    def check(
        self,
        *,
        extra_document_ids: Iterable[UUID] = (),
    ) -> ReconciliationReport:
        """
        Report drift and orphans without changing anything.

        `extra_document_ids` lets a caller supply document ids observed in the
        vector store (for example from a backend scan) so orphans with no
        document record can be detected.
        """
        documents = self._documents.list_all()
        drifted: list[DocumentDrift] = []

        for document in documents:
            chunks = self._chunks.list_by_document_id(document.id)
            if not chunks:
                continue
            statuses = {chunk.document_status for chunk in chunks}
            expected = (
                SEARCHABLE if document.status == DocumentStatus.INDEXED else None
            )
            observed = next(iter(statuses)) if len(statuses) == 1 else "mixed"

            searchable = observed == SEARCHABLE
            should_be_searchable = expected == SEARCHABLE
            if searchable != should_be_searchable or observed == "mixed":
                drifted.append(
                    DocumentDrift(
                        document_id=document.id,
                        document_status=document.status.value,
                        chunk_status=observed,
                        chunk_count=len(chunks),
                    )
                )

        known = {document.id for document in documents}
        orphans = tuple(
            document_id
            for document_id in dict.fromkeys(extra_document_ids)
            if document_id not in known
        )

        report = ReconciliationReport(
            checked_documents=len(documents),
            drifted=tuple(drifted),
            orphaned_document_ids=orphans,
        )
        self._log(report)
        return report

    def repair(self, report: ReconciliationReport | None = None) -> int:
        """
        Realign chunk status with the document record.

        Only touches drifted documents, and only sets status — it never deletes
        chunks, so a mistaken run cannot destroy data. Orphans are reported for
        an operator to remove deliberately.
        """
        target = report or self.check()
        repaired = 0
        for drift in target.drifted:
            document = self._documents.get(drift.document_id)
            if document is None:
                continue
            desired = (
                SEARCHABLE
                if document.status == DocumentStatus.INDEXED
                else DocumentStatus.PROCESSING.value
            )
            self._chunks.set_document_status(drift.document_id, desired)
            repaired += 1
        if repaired:
            logger.info("reconciliation repaired %d document(s)", repaired)
        return repaired

    def purge_orphans(self, document_ids: Sequence[UUID]) -> int:
        """
        Delete chunks for documents with no record. Explicit call only.

        This is the cleanup path for vectors stranded before the document store
        became durable.
        """
        deleted = 0
        for document_id in document_ids:
            if self._documents.get(document_id) is not None:
                # Never delete chunks for a document that still exists.
                continue
            deleted += self._chunks.delete_by_document_id(document_id)
        if deleted:
            logger.warning("reconciliation purged %d orphaned chunk(s)", deleted)
        return deleted

    @staticmethod
    def _log(report: ReconciliationReport) -> None:
        if report.is_clean:
            logger.info("reconciliation clean: %d document(s)", report.checked_documents)
            return
        if report.over_exposed:
            # Content reachable that should be hidden: the direction that matters.
            logger.critical(
                "reconciliation found %d over-exposed document(s)",
                len(report.over_exposed),
            )
        logger.warning(
            "reconciliation drift=%d orphans=%d",
            len(report.drifted),
            len(report.orphaned_document_ids),
        )
