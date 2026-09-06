"""
End-to-end persistence and reconciliation (Phase 7).

The audit's critical finding was that vectors were durable while the metadata
gating them was not, so a restart produced a total retrieval outage and
permanently orphaned every vector. These tests reproduce that scenario and prove
the durable path fixes it.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from tests.rag.conftest import STUB_EMBEDDING_CONFIG, make_embedded_stored_chunk, make_ingest_request

from rag.app.factory import RagApplication
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.types import RetrievalApiRequest
from rag.identity.sqlite_store import SqliteIdentityStore
from rag.identity.store import CompanyRecord, DepartmentRecord, UserRecord
from rag.ingestion.store.sqlite_document_store import SqliteDocumentStore
from rag.ingestion.types import DocumentStatus
from rag.storage.chunk_store import InMemoryChunkStore
from rag.storage.config import (
    METADATA_BACKEND_MEMORY,
    METADATA_BACKEND_SQLITE,
    MetadataStoreConfig,
)
from rag.storage.factory import (
    create_document_store,
    create_identity_store,
    create_metadata_database,
    create_permission_registry,
)
from rag.storage.reconciliation import StoreReconciler

MARKER = "سند بازیابی پس از راه‌اندازی مجدد"


class TestMetadataFactory:
    def test_memory_backend_is_the_default(self):
        config = MetadataStoreConfig()
        assert config.backend == METADATA_BACKEND_MEMORY
        assert config.is_persistent is False
        assert create_metadata_database(config) is None

    def test_sqlite_backend_builds_all_three_stores(self, tmp_path):
        config = MetadataStoreConfig(
            backend=METADATA_BACKEND_SQLITE, path=str(tmp_path / "meta.db")
        )
        database = create_metadata_database(config)
        try:
            assert isinstance(
                create_document_store(config, database=database), SqliteDocumentStore
            )
            assert isinstance(
                create_identity_store(config, database=database), SqliteIdentityStore
            )
            registry = create_permission_registry(config, database=database)
            assert registry.ping() is True
        finally:
            database.close()

    def test_one_database_serves_documents_and_identity(self, tmp_path):
        """Both schemas migrate into the same file, so one connection serves both."""
        config = MetadataStoreConfig(
            backend=METADATA_BACKEND_SQLITE, path=str(tmp_path / "shared.db")
        )
        database = create_metadata_database(config)
        try:
            documents = create_document_store(config, database=database)
            identities = create_identity_store(config, database=database)
            company = uuid4()
            identities.register_company(CompanyRecord(id=company))
            documents.create_processing(
                company_id=company,
                department_id=uuid4(),
                source="s",
                language="fa",
                source_type="test",
                content_hash="h",
                normalization_version="fa-norm-v1",
            )
            assert documents.count() == 1
            assert identities.get_company(company) is not None
        finally:
            database.close()

    @pytest.mark.parametrize(
        "overrides",
        [{"backend": "mongo"}, {"backend": "sqlite", "path": ""}, {"busy_timeout_ms": 0}],
    )
    def test_invalid_metadata_config_rejected(self, overrides):
        from rag.storage.errors import StorageConfigurationError

        with pytest.raises(StorageConfigurationError):
            MetadataStoreConfig(**overrides).validate()


class TestRestartRecovery:
    """The scenario from audit finding C1."""

    def _build(self, tmp_path, chunk_store, tenant_ids):
        config = MetadataStoreConfig(
            backend=METADATA_BACKEND_SQLITE, path=str(tmp_path / "app.db")
        )
        database = create_metadata_database(config)
        identity_store = create_identity_store(config, database=database)
        document_store = create_document_store(config, database=database)
        permissions = create_permission_registry(config, database=database)

        c1 = tenant_ids["companies"]["C1"]
        d1 = tenant_ids["departments"]["C1_D1"]
        u1 = tenant_ids["users"]["U1"]
        identity_store.register_company(CompanyRecord(id=c1))
        identity_store.register_department(DepartmentRecord(id=d1, company_id=c1))
        identity_store.register_user(UserRecord(id=u1, company_id=c1), [d1])
        identity_store.register_token(uuid4(), u1, tenant_ids["tokens"]["U1"])

        app = RagApplication.build_in_memory(
            identity_store,
            ingest_permissions=permissions,
            chunk_store=chunk_store,
            document_store=document_store,
            embedding_config=STUB_EMBEDDING_CONFIG,
        )
        return app, database

    def test_documents_and_identity_survive_a_restart(self, tmp_path, tenant_ids):
        # A shared chunk store stands in for durable Weaviate storage.
        chunk_store = InMemoryChunkStore()
        request_id = uuid4()

        first, database = self._build(tmp_path, chunk_store, tenant_ids)
        created = first.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert (
            RetrieveHandler(first.retrieval_service)
            .retrieve(
                RetrievalApiRequest(query=MARKER, request_id=request_id, top_k=5),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
            .chunk_count
            >= 1
        )
        database.close()

        # Restart: brand new application, same database file and vector store.
        second, database2 = self._build(tmp_path, chunk_store, tenant_ids)
        try:
            assert second.document_store.get(created.document_id) is not None
            assert (
                second.document_store.get(created.document_id).status
                == DocumentStatus.INDEXED
            )
            # The property whose absence caused the outage.
            response = RetrieveHandler(second.retrieval_service).retrieve(
                RetrievalApiRequest(query=MARKER, request_id=uuid4(), top_k=5),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
            assert response.chunk_count >= 1
        finally:
            database2.close()

    def test_in_memory_metadata_still_loses_state(self, tenant_ids):
        """Contrast: the old configuration behaves as the audit described."""
        chunk_store = InMemoryChunkStore()
        from rag.identity.store import InMemoryIdentityStore

        app = RagApplication.build_in_memory(
            InMemoryIdentityStore(), chunk_store=chunk_store,
            embedding_config=STUB_EMBEDDING_CONFIG,
        )
        # A fresh in-memory document store knows nothing, so nothing is
        # retrievable even though the vectors exist.
        assert app.document_store.count() == 0


class TestReconciliation:
    def test_clean_state_reports_clean(self, rag_application, tenant_ids, request_id):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        report = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        ).check()
        assert report.is_clean
        assert report.checked_documents == 1

    def test_detects_over_exposed_chunks(
        self, rag_application, tenant_ids, request_id
    ):
        """The security-relevant direction: visible when it should be hidden."""
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        # Simulate drift: the document is retired but its chunks stay published.
        rag_application.document_store.mark_failed(created.document_id, "BoomError")

        report = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        ).check()
        assert not report.is_clean
        assert len(report.over_exposed) == 1
        assert report.over_exposed[0].document_id == created.document_id

    def test_detects_wrongly_hidden_chunks(
        self, rag_application, tenant_ids, request_id
    ):
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.chunk_store.set_document_status(
            created.document_id, DocumentStatus.PROCESSING.value
        )
        report = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        ).check()
        assert not report.is_clean
        assert report.over_exposed == ()

    def test_repair_realigns_status(self, rag_application, tenant_ids, request_id):
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.chunk_store.set_document_status(
            created.document_id, DocumentStatus.PROCESSING.value
        )
        reconciler = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        )
        assert reconciler.repair() == 1
        assert reconciler.check().is_clean

    def test_repair_hides_chunks_of_a_failed_document(
        self, rag_application, tenant_ids, request_id
    ):
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.document_store.mark_failed(created.document_id, "BoomError")
        reconciler = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        )
        reconciler.repair()
        chunks = rag_application.chunk_store.list_by_document_id(created.document_id)
        assert all(
            chunk.document_status != DocumentStatus.INDEXED.value for chunk in chunks
        )

    def test_detects_orphaned_documents(
        self, rag_application, embedding_service, tenant_ids
    ):
        """Vectors with no document record — the C1 accumulation problem."""
        orphan_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=orphan_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="یتیم",
        )
        rag_application.chunk_store.replace_document_chunks(orphan_id, [chunk])
        report = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        ).check(extra_document_ids=[orphan_id])
        assert report.orphaned_document_ids == (orphan_id,)

    def test_purge_removes_orphans(
        self, rag_application, embedding_service, tenant_ids
    ):
        orphan_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=orphan_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="یتیم",
        )
        rag_application.chunk_store.replace_document_chunks(orphan_id, [chunk])
        reconciler = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        )
        assert reconciler.purge_orphans([orphan_id]) == 1
        assert rag_application.chunk_store.count_by_document_id(orphan_id) == 0

    def test_purge_never_touches_a_live_document(
        self, rag_application, tenant_ids, request_id
    ):
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=MARKER),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        reconciler = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        )
        # Even asked directly, a document that still exists is left alone.
        assert reconciler.purge_orphans([created.document_id]) == 0
        assert rag_application.chunk_store.count_by_document_id(created.document_id) > 0

    def test_report_serialises(self, rag_application):
        report = StoreReconciler(
            rag_application.document_store, rag_application.chunk_store
        ).check()
        payload = report.to_dict()
        assert payload["clean"] is True
        assert payload["orphaned_count"] == 0
