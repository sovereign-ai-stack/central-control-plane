"""OWN-* ownership and chunk metadata propagation tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.ingestion.errors import IngestNotFoundError, IngestPipelineError
from rag.ingestion.types import DocumentStatus, IngestDocumentUpdateRequest
from rag.storage.chunk_store import InMemoryChunkStore
from tests.rag.conftest import SAMPLE_PERSIAN_CONTENT, make_embedded_stored_chunk, make_ingest_request


@pytest.mark.security
class TestIngestionOwnership:
    def test_own_001_chunk_scope_matches_document(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        request = make_ingest_request(tenant_ids)
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        chunks = chunk_store.list_by_document_id(response.document_id)
        for chunk in chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
            assert chunk.department_id == tenant_ids["departments"]["C1_D1"]
            assert chunk.document_id == response.document_id

    def test_own_002_update_preserves_ownership(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        request = make_ingest_request(tenant_ids)
        created = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        update = IngestDocumentUpdateRequest(
            content=SAMPLE_PERSIAN_CONTENT + " محتوای به‌روز شده.",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            source="test-fixture",
        )
        updated = ingestion_service.update_document(
            created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
        )
        chunks = chunk_store.list_by_document_id(updated.document_id)
        for chunk in chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
            assert chunk.department_id == tenant_ids["departments"]["C1_D1"]

    def test_own_003_pipeline_aborts_on_metadata_failure(
        self, ingestion_service, tenant_ids, request_id, chunk_store, document_store, monkeypatch
    ):
        from rag.ingestion import pipeline as pipeline_module

        def fail_metadata(*args, **kwargs):
            raise IngestPipelineError("chunk missing mandatory security metadata")

        monkeypatch.setattr(pipeline_module, "build_stored_chunks", fail_metadata)
        with pytest.raises(IngestPipelineError):
            ingestion_service.create_document(
                make_ingest_request(tenant_ids),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        documents = document_store.list_all()
        assert len(documents) == 1
        assert documents[0].status.value == "failed"
        assert chunk_store.count_by_document_id(documents[0].id) == 0

    def test_own_004_chunk_scope_mismatch_rejected(self, tenant_ids, embedding_service):
        store = InMemoryChunkStore()
        doc_id = uuid4()
        c1 = tenant_ids["companies"]["C1"]
        d1 = tenant_ids["departments"]["C1_D1"]
        d2 = tenant_ids["departments"]["C1_D2"]

        chunks = [
            make_embedded_stored_chunk(
                embedding_service,
                chunk_id=uuid4(),
                document_id=doc_id,
                company_id=c1,
                department_id=d1,
                content="chunk one",
                chunk_index=0,
            ),
            make_embedded_stored_chunk(
                embedding_service,
                chunk_id=uuid4(),
                document_id=doc_id,
                company_id=c1,
                department_id=d2,
                content="chunk two",
                chunk_index=1,
            ),
        ]
        with pytest.raises(ValueError, match="security scope mismatch"):
            store.replace_document_chunks(doc_id, chunks)

    def test_own_005_delete_removes_all_chunks(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        request = make_ingest_request(tenant_ids)
        created = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["U1"]
        )
        assert chunk_store.count_by_document_id(created.document_id) == 0


@pytest.mark.security
class TestUnauthorizedDocumentAccess:
    def _create_in_d2(self, ingestion_service, tenant_ids, request_id):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        return ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["S1"]
        )

    def test_unauthorized_update_by_document_id(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        created = self._create_in_d2( ingestion_service, tenant_ids, request_id)
        update = IngestDocumentUpdateRequest(
            content=SAMPLE_PERSIAN_CONTENT + " update attempt",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D2"],
        )
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.update_document(
                created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
            )
        assert chunk_store.count_by_document_id(created.document_id) > 0

    def test_unauthorized_delete(
        self, ingestion_service, tenant_ids, request_id, chunk_store, document_store
    ):
        created = self._create_in_d2(ingestion_service, tenant_ids, request_id)
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.delete_document(
                created.document_id, request_id, tenant_ids["tokens"]["U1"]
            )
        document = document_store.get(created.document_id)
        assert document is not None
        assert document.status == DocumentStatus.INDEXED
        assert chunk_store.count_by_document_id(created.document_id) > 0

    def test_scope_tampering_on_update_rejected(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        update = IngestDocumentUpdateRequest(
            content=SAMPLE_PERSIAN_CONTENT,
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
        )
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.update_document(
                created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
            )
        document = document_store.get(created.document_id)
        assert document is not None
        assert document.company_id == tenant_ids["companies"]["C1"]

    def test_delete_nonexistent_document(self, ingestion_service, tenant_ids, request_id):
        with pytest.raises(IngestNotFoundError):
            ingestion_service.delete_document(
                uuid4(), request_id, tenant_ids["tokens"]["U1"]
            )
