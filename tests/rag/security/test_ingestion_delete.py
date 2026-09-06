"""DEL-* delete authorization tests."""

from __future__ import annotations

import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.ingestion.types import DocumentStatus
from tests.rag.conftest import make_embedded_stored_chunk, make_ingest_request


@pytest.mark.security
class TestIngestionDelete:
    def _ingest_c1_d1(self, ingestion_service, tenant_ids, request_id, token_key="U1"):
        return ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"][token_key],
        )

    def _ingest_c1_d2(self, ingestion_service, tenant_ids, request_id):
        return ingestion_service.create_document(
            make_ingest_request(tenant_ids, department_key="C1_D2"),
            request_id,
            tenant_ids["tokens"]["S1"],
        )

    def test_del_001_owner_can_delete(
        self, ingestion_service, tenant_ids, request_id, document_store, chunk_store
    ):
        created = self._ingest_c1_d1(ingestion_service, tenant_ids, request_id)
        ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["U1"]
        )
        document = document_store.get(created.document_id)
        assert document is not None
        assert document.status == DocumentStatus.DELETED
        assert chunk_store.count_by_document_id(created.document_id) == 0

    def test_del_002_cross_department_delete_denied(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        created = self._ingest_c1_d2(ingestion_service, tenant_ids, request_id)
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.delete_document(
                created.document_id, request_id, tenant_ids["tokens"]["U1"]
            )
        assert chunk_store.count_by_document_id(created.document_id) > 0

    def test_del_003_cross_company_delete_denied(
        self,
        ingestion_service,
        tenant_ids,
        request_id,
        document_store,
        chunk_store,
        embedding_service,
    ):
        from uuid import uuid4

        doc_id = uuid4()
        c2 = tenant_ids["companies"]["C2"]
        d2 = tenant_ids["departments"]["C2_D1"]
        document_store.create_processing(
            company_id=c2,
            department_id=d2,
            source="seed",
            language="fa",
            source_type="test",
            content_hash="abc",
            normalization_version="fa-norm-v1",
            document_id=doc_id,
        )
        document_store.mark_indexed(doc_id, chunk_count=1, content_hash="abc")
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=doc_id,
            company_id=c2,
            department_id=d2,
            content="c2 content",
        )
        chunk_store.replace_document_chunks(doc_id, [chunk])

        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.delete_document(
                doc_id, request_id, tenant_ids["tokens"]["U1"]
            )
        assert chunk_store.count_by_document_id(doc_id) == 1

    def test_del_004_company_wide_can_delete(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        created = self._ingest_c1_d2(ingestion_service, tenant_ids, request_id)
        ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["S1"]
        )
        assert chunk_store.count_by_document_id(created.document_id) == 0
