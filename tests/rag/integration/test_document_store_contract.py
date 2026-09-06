"""
Backend-agnostic `DocumentStore` conformance suite (Phase 7).

Stated against the protocol, never against one implementation — the same
approach as the `ChunkStore` suite. Both the in-memory and SQLite stores must
satisfy it identically, plus a durability section that only a persistent backend
can pass.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag.ingestion.store.document_store import DocumentStore, InMemoryDocumentStore
from rag.ingestion.store.sqlite_document_store import (
    MIGRATIONS,
    SqliteDocumentStore,
)
from rag.ingestion.types import DocumentStatus
from rag.storage.db import SqliteDatabase

BACKENDS = ["in_memory", "sqlite"]


@pytest.fixture(params=BACKENDS, ids=BACKENDS)
def store(request, tmp_path) -> DocumentStore:
    if request.param == "in_memory":
        return InMemoryDocumentStore()
    database = SqliteDatabase(tmp_path / "documents.db", migrations=MIGRATIONS)
    backend = SqliteDocumentStore(database)
    request.addfinalizer(backend.close)
    return backend


@pytest.fixture
def scope(tenant_ids):
    return {
        "company_id": tenant_ids["companies"]["C1"],
        "department_id": tenant_ids["departments"]["C1_D1"],
    }


def create(store, scope, **overrides):
    payload = {
        "company_id": scope["company_id"],
        "department_id": scope["department_id"],
        "source": "conformance",
        "language": "fa",
        "source_type": "test",
        "content_hash": "hash-1",
        "normalization_version": "fa-norm-v1",
    }
    payload.update(overrides)
    return store.create_processing(**payload)


class TestProtocolConformance:
    def test_store_satisfies_the_protocol(self, store):
        assert isinstance(store, DocumentStore)

    def test_create_returns_a_processing_document(self, store, scope):
        record = create(store, scope)
        assert record.status == DocumentStatus.PROCESSING
        assert record.version == 1
        assert record.chunk_count == 0
        assert record.created_at is not None

    def test_get_returns_the_created_record(self, store, scope):
        record = create(store, scope)
        fetched = store.get(record.id)
        assert fetched is not None
        assert fetched.id == record.id
        assert fetched.company_id == scope["company_id"]
        assert fetched.department_id == scope["department_id"]

    def test_all_fields_round_trip(self, store, scope):
        record = create(
            store,
            scope,
            title="راهنمای منابع انسانی",
            source_uri="s3://bucket/key.pdf",
            source_type="pdf",
            language="fa",
            content_hash="hash-round-trip",
            normalization_version="fa-norm-v2",
        )
        fetched = store.get(record.id)
        assert fetched.title == "راهنمای منابع انسانی"
        assert fetched.source_uri == "s3://bucket/key.pdf"
        assert fetched.source_type == "pdf"
        assert fetched.normalization_version == "fa-norm-v2"
        assert fetched.content_hash == "hash-round-trip"

    def test_unknown_document_is_none(self, store):
        assert store.get(uuid4()) is None

    def test_count_and_list_all(self, store, scope):
        assert store.count() == 0
        first = create(store, scope, document_id=uuid4())
        second = create(store, scope, document_id=uuid4(), content_hash="hash-2")
        assert store.count() == 2
        ids = {record.id for record in store.list_all()}
        assert ids == {first.id, second.id}

    def test_duplicate_document_id_rejected(self, store, scope):
        record = create(store, scope)
        with pytest.raises(ValueError, match="already exists"):
            create(store, scope, document_id=record.id)

    def test_deleted_document_id_may_be_recreated(self, store, scope):
        record = create(store, scope)
        store.mark_deleted(record.id)
        recreated = create(store, scope, document_id=record.id)
        assert recreated.status == DocumentStatus.PROCESSING
        assert store.get(record.id).status == DocumentStatus.PROCESSING


class TestStatusTransitions:
    def test_mark_indexed(self, store, scope):
        record = create(store, scope)
        updated = store.mark_indexed(record.id, chunk_count=7, content_hash="hash-x")
        assert updated.status == DocumentStatus.INDEXED
        assert updated.chunk_count == 7
        assert updated.content_hash == "hash-x"
        assert updated.indexed_at is not None
        assert store.get(record.id).status == DocumentStatus.INDEXED

    def test_mark_indexed_clears_prior_failure(self, store, scope):
        record = create(store, scope)
        store.mark_failed(record.id, "BoomError")
        store.mark_indexed(record.id, chunk_count=1, content_hash="hash-y")
        fetched = store.get(record.id)
        assert fetched.failed_at is None
        assert fetched.failure_reason is None

    def test_mark_indexed_can_bump_version(self, store, scope):
        record = create(store, scope)
        store.mark_indexed(record.id, chunk_count=1, content_hash="h", version=4)
        assert store.get(record.id).version == 4

    def test_mark_failed(self, store, scope):
        record = create(store, scope)
        updated = store.mark_failed(record.id, "IngestEmbeddingError")
        assert updated.status == DocumentStatus.FAILED
        assert updated.chunk_count == 0
        assert store.get(record.id).failure_reason == "IngestEmbeddingError"

    def test_mark_deleted(self, store, scope):
        record = create(store, scope)
        store.mark_indexed(record.id, chunk_count=3, content_hash="h")
        updated = store.mark_deleted(record.id)
        assert updated.status == DocumentStatus.DELETED
        assert updated.chunk_count == 0
        assert store.get(record.id).status == DocumentStatus.DELETED

    def test_begin_reindex_moves_to_processing(self, store, scope):
        record = create(store, scope)
        store.mark_indexed(record.id, chunk_count=2, content_hash="old")
        store.begin_reindex(record.id, "new-hash")
        fetched = store.get(record.id)
        assert fetched.status == DocumentStatus.PROCESSING
        assert fetched.content_hash == "new-hash"

    @pytest.mark.parametrize(
        "operation",
        ["mark_indexed", "mark_failed", "mark_deleted", "begin_reindex"],
    )
    def test_operations_on_unknown_document_raise(self, store, operation):
        unknown = uuid4()
        with pytest.raises(KeyError):
            if operation == "mark_indexed":
                store.mark_indexed(unknown, chunk_count=1, content_hash="h")
            elif operation == "mark_failed":
                store.mark_failed(unknown, "reason")
            elif operation == "mark_deleted":
                store.mark_deleted(unknown)
            else:
                store.begin_reindex(unknown, "h")


class TestDeduplicationLookup:
    def test_finds_only_indexed_documents(self, store, scope):
        record = create(store, scope, content_hash="dedup-hash")
        # PROCESSING must not match.
        assert (
            store.find_indexed_by_content_hash(
                scope["company_id"], scope["department_id"], "dedup-hash"
            )
            is None
        )
        store.mark_indexed(record.id, chunk_count=1, content_hash="dedup-hash")
        found = store.find_indexed_by_content_hash(
            scope["company_id"], scope["department_id"], "dedup-hash"
        )
        assert found is not None
        assert found.id == record.id

    def test_scoped_to_company_and_department(self, store, scope, tenant_ids):
        record = create(store, scope, content_hash="scoped-hash")
        store.mark_indexed(record.id, chunk_count=1, content_hash="scoped-hash")

        # Another company must not see it.
        assert (
            store.find_indexed_by_content_hash(
                tenant_ids["companies"]["C2"],
                scope["department_id"],
                "scoped-hash",
            )
            is None
        )
        # Another department must not see it.
        assert (
            store.find_indexed_by_content_hash(
                scope["company_id"],
                tenant_ids["departments"]["C1_D2"],
                "scoped-hash",
            )
            is None
        )

    def test_deleted_document_is_not_a_duplicate(self, store, scope):
        record = create(store, scope, content_hash="gone")
        store.mark_indexed(record.id, chunk_count=1, content_hash="gone")
        store.mark_deleted(record.id)
        assert (
            store.find_indexed_by_content_hash(
                scope["company_id"], scope["department_id"], "gone"
            )
            is None
        )


class TestIndexedScopeQuery:
    def test_returns_only_indexed_in_scope(self, store, scope, tenant_ids):
        indexed = create(store, scope, document_id=uuid4(), content_hash="a")
        store.mark_indexed(indexed.id, chunk_count=1, content_hash="a")
        create(store, scope, document_id=uuid4(), content_hash="b")  # PROCESSING

        other_department = create(
            store,
            {
                "company_id": scope["company_id"],
                "department_id": tenant_ids["departments"]["C1_D2"],
            },
            document_id=uuid4(),
            content_hash="c",
        )
        store.mark_indexed(other_department.id, chunk_count=1, content_hash="c")

        result = store.list_indexed_ids(
            scope["company_id"], (scope["department_id"],)
        )
        assert result == frozenset({indexed.id})

    def test_empty_department_scope_returns_nothing(self, store, scope):
        record = create(store, scope)
        store.mark_indexed(record.id, chunk_count=1, content_hash="h")
        assert store.list_indexed_ids(scope["company_id"], ()) == frozenset()

    def test_other_company_returns_nothing(self, store, scope, tenant_ids):
        record = create(store, scope)
        store.mark_indexed(record.id, chunk_count=1, content_hash="h")
        assert (
            store.list_indexed_ids(
                tenant_ids["companies"]["C2"], (scope["department_id"],)
            )
            == frozenset()
        )


class TestAvailability:
    def test_ping_reports_healthy(self, store):
        assert store.ping() is True


class TestDurability:
    """Only a persistent backend can pass these."""

    def test_records_survive_a_reopen(self, tmp_path, scope):
        path = tmp_path / "durable.db"
        first = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        record = create(first, scope, title="پایدار")
        first.mark_indexed(record.id, chunk_count=5, content_hash="persisted")
        first.close()

        # Simulate a process restart.
        second = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        try:
            reopened = second.get(record.id)
            assert reopened is not None
            assert reopened.status == DocumentStatus.INDEXED
            assert reopened.chunk_count == 5
            assert reopened.content_hash == "persisted"
            assert reopened.title == "پایدار"
        finally:
            second.close()

    def test_indexed_scope_survives_a_reopen(self, tmp_path, scope):
        path = tmp_path / "durable-scope.db"
        first = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        record = create(first, scope)
        first.mark_indexed(record.id, chunk_count=1, content_hash="h")
        first.close()

        second = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        try:
            # This is the property whose absence caused the retrieval outage:
            # after a restart the document must still be searchable.
            assert second.list_indexed_ids(
                scope["company_id"], (scope["department_id"],)
            ) == frozenset({record.id})
        finally:
            second.close()

    def test_in_memory_store_does_not_persist(self, scope):
        first = InMemoryDocumentStore()
        record = create(first, scope)
        assert InMemoryDocumentStore().get(record.id) is None

    def test_migrations_are_idempotent(self, tmp_path, scope):
        path = tmp_path / "migrate.db"
        for _ in range(3):
            store = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
            store.close()
        store = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        try:
            assert store.count() == 0
            create(store, scope)
            assert store.count() == 1
        finally:
            store.close()

    def test_timestamps_survive_with_timezone(self, tmp_path, scope):
        path = tmp_path / "tz.db"
        first = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        record = create(first, scope)
        first.close()

        second = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        try:
            fetched = second.get(record.id)
            assert fetched.created_at.tzinfo is not None
            assert fetched.created_at == record.created_at
        finally:
            second.close()


class TestConcurrency:
    def test_concurrent_writes_from_threads(self, tmp_path, scope):
        """WAL plus per-thread connections must tolerate parallel writers."""
        import threading

        path = tmp_path / "concurrent.db"
        store = SqliteDocumentStore(SqliteDatabase(path, migrations=MIGRATIONS))
        errors: list[Exception] = []

        def writer(index: int) -> None:
            try:
                create(
                    store,
                    scope,
                    document_id=uuid4(),
                    content_hash=f"hash-{index}",
                )
            except Exception as exc:  # noqa: BLE001 - recorded and asserted below
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        try:
            assert errors == []
            assert store.count() == 12
        finally:
            store.close()
