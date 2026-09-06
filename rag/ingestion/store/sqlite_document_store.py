"""
Durable document metadata store backed by SQLite.

Satisfies the same `DocumentStore` protocol as the in-memory implementation and
is verified by the same conformance suite.

`find_indexed_by_content_hash` and `list_indexed_ids` are indexed queries here,
where the in-memory store scans every record — persistence is faster for the
lookups that matter, not just more durable.

PostgreSQL path: the SQL is parameterised and portable. A Postgres class would
change the placeholder style and the `Database` seam, not this logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from rag.ingestion.store.document_store import utc_now
from rag.ingestion.types import DocumentRecord, DocumentStatus
from rag.storage.db import SqliteDatabase

MIGRATIONS = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id                    TEXT PRIMARY KEY,
        company_id            TEXT    NOT NULL,
        department_id         TEXT    NOT NULL,
        title                 TEXT,
        source                TEXT    NOT NULL,
        language              TEXT    NOT NULL,
        source_type           TEXT    NOT NULL,
        source_uri            TEXT,
        version               INTEGER NOT NULL,
        status                TEXT    NOT NULL,
        content_hash          TEXT    NOT NULL,
        normalization_version TEXT    NOT NULL,
        chunk_count           INTEGER NOT NULL,
        created_at            TEXT    NOT NULL,
        updated_at            TEXT    NOT NULL,
        indexed_at            TEXT,
        failed_at             TEXT,
        failure_reason        TEXT
    )
    """,
    # Scope lookups are always company + department + status.
    """
    CREATE INDEX IF NOT EXISTS idx_documents_scope
        ON documents (company_id, department_id, status)
    """,
    # Deduplication lookup.
    """
    CREATE INDEX IF NOT EXISTS idx_documents_content_hash
        ON documents (company_id, department_id, content_hash, status)
    """,
)

_COLUMNS = (
    "id, company_id, department_id, title, source, language, source_type, "
    "source_uri, version, status, content_hash, normalization_version, "
    "chunk_count, created_at, updated_at, indexed_at, failed_at, failure_reason"
)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _row_to_record(row) -> DocumentRecord:
    return DocumentRecord(
        id=UUID(row["id"]),
        company_id=UUID(row["company_id"]),
        department_id=UUID(row["department_id"]),
        title=row["title"],
        source=row["source"],
        language=row["language"],
        source_type=row["source_type"],
        source_uri=row["source_uri"],
        version=int(row["version"]),
        status=DocumentStatus(row["status"]),
        content_hash=row["content_hash"],
        normalization_version=row["normalization_version"],
        chunk_count=int(row["chunk_count"]),
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
        indexed_at=_parse_datetime(row["indexed_at"]),
        failed_at=_parse_datetime(row["failed_at"]),
        failure_reason=row["failure_reason"],
    )


class SqliteDocumentStore:
    """Document metadata that survives a restart."""

    def __init__(self, database: SqliteDatabase | None = None) -> None:
        self._db = database or SqliteDatabase(migrations=MIGRATIONS)

    @property
    def database(self) -> SqliteDatabase:
        return self._db

    def count(self) -> int:
        row = self._db.query_one("SELECT COUNT(*) AS total FROM documents")
        return int(row["total"]) if row else 0

    def list_all(self) -> list[DocumentRecord]:
        rows = self._db.query_all(f"SELECT {_COLUMNS} FROM documents")
        return [_row_to_record(row) for row in rows]

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

        existing = self.get(doc_id)
        if existing is not None and existing.status != DocumentStatus.DELETED:
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
        with self._db.write() as connection:
            # A re-created DELETED document replaces the tombstone row.
            connection.execute(
                "INSERT OR REPLACE INTO documents "
                f"({_COLUMNS}) VALUES ({', '.join('?' * 18)})",
                (
                    str(record.id),
                    str(record.company_id),
                    str(record.department_id),
                    record.title,
                    record.source,
                    record.language,
                    record.source_type,
                    record.source_uri,
                    record.version,
                    record.status.value,
                    record.content_hash,
                    record.normalization_version,
                    record.chunk_count,
                    _iso(record.created_at),
                    _iso(record.updated_at),
                    None,
                    None,
                    None,
                ),
            )
        return record

    def get(self, document_id: UUID) -> DocumentRecord | None:
        row = self._db.query_one(
            f"SELECT {_COLUMNS} FROM documents WHERE id = ?", (str(document_id),)
        )
        return None if row is None else _row_to_record(row)

    def find_indexed_by_content_hash(
        self,
        company_id: UUID,
        department_id: UUID,
        content_hash: str,
    ) -> DocumentRecord | None:
        row = self._db.query_one(
            f"SELECT {_COLUMNS} FROM documents "
            "WHERE company_id = ? AND department_id = ? AND content_hash = ? "
            "AND status = ? LIMIT 1",
            (
                str(company_id),
                str(department_id),
                content_hash,
                DocumentStatus.INDEXED.value,
            ),
        )
        return None if row is None else _row_to_record(row)

    def mark_indexed(
        self,
        document_id: UUID,
        *,
        chunk_count: int,
        content_hash: str,
        version: int | None = None,
    ) -> DocumentRecord:
        document = self._require(document_id)
        now = utc_now()
        document.status = DocumentStatus.INDEXED
        document.chunk_count = chunk_count
        document.content_hash = content_hash
        document.updated_at = now
        document.indexed_at = now
        document.failed_at = None
        document.failure_reason = None
        if version is not None:
            document.version = version

        with self._db.write() as connection:
            connection.execute(
                "UPDATE documents SET status = ?, chunk_count = ?, content_hash = ?, "
                "updated_at = ?, indexed_at = ?, failed_at = NULL, "
                "failure_reason = NULL, version = ? WHERE id = ?",
                (
                    document.status.value,
                    document.chunk_count,
                    document.content_hash,
                    _iso(document.updated_at),
                    _iso(document.indexed_at),
                    document.version,
                    str(document_id),
                ),
            )
        return document

    def mark_failed(self, document_id: UUID, reason: str) -> DocumentRecord:
        document = self._require(document_id)
        now = utc_now()
        document.status = DocumentStatus.FAILED
        document.chunk_count = 0
        document.failed_at = now
        document.failure_reason = reason
        document.updated_at = now

        with self._db.write() as connection:
            connection.execute(
                "UPDATE documents SET status = ?, chunk_count = 0, failed_at = ?, "
                "failure_reason = ?, updated_at = ? WHERE id = ?",
                (
                    document.status.value,
                    _iso(document.failed_at),
                    reason,
                    _iso(document.updated_at),
                    str(document_id),
                ),
            )
        return document

    def mark_deleted(self, document_id: UUID) -> DocumentRecord:
        document = self._require(document_id)
        document.status = DocumentStatus.DELETED
        document.chunk_count = 0
        document.updated_at = utc_now()

        with self._db.write() as connection:
            connection.execute(
                "UPDATE documents SET status = ?, chunk_count = 0, updated_at = ? "
                "WHERE id = ?",
                (
                    document.status.value,
                    _iso(document.updated_at),
                    str(document_id),
                ),
            )
        return document

    def begin_reindex(self, document_id: UUID, content_hash: str) -> DocumentRecord:
        document = self._require(document_id)
        document.status = DocumentStatus.PROCESSING
        document.content_hash = content_hash
        document.updated_at = utc_now()

        with self._db.write() as connection:
            connection.execute(
                "UPDATE documents SET status = ?, content_hash = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    document.status.value,
                    content_hash,
                    _iso(document.updated_at),
                    str(document_id),
                ),
            )
        return document

    def list_indexed_ids(
        self,
        company_id: UUID,
        department_ids: tuple[UUID, ...],
    ) -> frozenset[UUID]:
        if not department_ids:
            return frozenset()
        placeholders = ", ".join("?" * len(department_ids))
        rows = self._db.query_all(
            "SELECT id FROM documents WHERE company_id = ? AND status = ? "
            f"AND department_id IN ({placeholders})",
            (
                str(company_id),
                DocumentStatus.INDEXED.value,
                *[str(value) for value in department_ids],
            ),
        )
        return frozenset(UUID(row["id"]) for row in rows)

    def ping(self) -> bool:
        return self._db.ping()

    def close(self) -> None:
        self._db.close()

    def _require(self, document_id: UUID) -> DocumentRecord:
        document = self.get(document_id)
        if document is None:
            raise KeyError(f"document not found: {document_id}")
        return document
