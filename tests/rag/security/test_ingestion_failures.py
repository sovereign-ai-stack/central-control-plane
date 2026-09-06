"""FAIL-ING-* and AUD-ING-* tests."""

from __future__ import annotations

import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.ingestion.errors import IngestPipelineError
from rag.ingestion.types import DocumentStatus, IngestDocumentUpdateRequest
from tests.rag.conftest import SAMPLE_PERSIAN_CONTENT, make_ingest_request


@pytest.mark.security
class TestIngestionFailureCases:
    def test_fail_ing_001_authz_failure_no_side_effects(
        self, ingestion_service, tenant_ids, request_id, document_store, chunk_store
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert document_store.count() == 0
        assert len(chunk_store._chunks) == 0

    def test_fail_ing_002_pipeline_failure_zero_chunks(
        self, ingestion_service, tenant_ids, request_id, chunk_store, document_store
    ):
        chunk_store.set_fail_on_write(True)
        request = make_ingest_request(tenant_ids)
        with pytest.raises(IngestPipelineError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        documents = document_store.list_all()
        assert len(documents) == 1
        assert documents[0].status == DocumentStatus.FAILED
        assert documents[0].chunk_count == 0
        assert chunk_store.count_by_document_id(documents[0].id) == 0

    def test_fail_ing_003_partial_write_rollback(
        self, ingestion_service, tenant_ids, request_id, chunk_store, document_store
    ):
        chunk_store.set_fail_on_write(True)
        request = make_ingest_request(tenant_ids)
        with pytest.raises(IngestPipelineError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert len(chunk_store._chunks) == 0
        assert document_store.list_all()[0].status == DocumentStatus.FAILED

    def test_fail_ing_004_error_does_not_leak_content(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        secret = "SECRET-CONTENT-LEAK-TEST-12345"
        chunk_store.set_fail_on_write(True)
        request = make_ingest_request(tenant_ids, content=secret * 20)
        with pytest.raises(IngestPipelineError) as exc:
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert secret not in str(exc.value)


@pytest.mark.security
class TestIngestionAuditEvents:
    def test_aud_ing_001_completed(
        self, ingestion_service, tenant_ids, request_id, ingestion_pipeline
    ):
        ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        completed = [
            e for e in ingestion_pipeline.audit_log.events if e.name == "ingestion.completed"
        ]
        assert len(completed) == 1
        event = completed[0]
        assert event.request_id == request_id
        fields = event.fields
        assert "document_id" in fields
        assert "company_id" in fields
        assert "department_id" in fields
        assert "chunk_count" in fields
        assert "content" not in fields

    def test_aud_ing_002_rejected(
        self, ingestion_service, tenant_ids, request_id, ingestion_pipeline
    ):
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                make_ingest_request(tenant_ids, department_key="C1_D2"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        rejected = [
            e for e in ingestion_pipeline.audit_log.events if e.name == "ingestion.rejected"
        ]
        assert len(rejected) == 1
        assert "reason" in rejected[0].fields
        assert "content" not in rejected[0].fields

    def test_aud_ing_003_failed(
        self, ingestion_service, tenant_ids, request_id, chunk_store, ingestion_pipeline
    ):
        chunk_store.set_fail_on_write(True)
        with pytest.raises(IngestPipelineError):
            ingestion_service.create_document(
                make_ingest_request(tenant_ids),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        failed = [e for e in ingestion_pipeline.audit_log.events if e.name == "ingestion.failed"]
        assert len(failed) == 1
        assert "failure_reason" in failed[0].fields
        assert "content" not in failed[0].fields

    def test_aud_ing_004_deleted(
        self, ingestion_service, tenant_ids, request_id, ingestion_pipeline
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["U1"]
        )
        deleted = [e for e in ingestion_pipeline.audit_log.events if e.name == "ingestion.deleted"]
        assert len(deleted) == 1
        assert deleted[0].fields["document_id"] == created.document_id

    def test_update_failure_preserves_old_chunks(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        prior_count = chunk_store.count_by_document_id(created.document_id)
        chunk_store.set_fail_on_write(True)
        update = IngestDocumentUpdateRequest(
            content=SAMPLE_PERSIAN_CONTENT + " updated",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        with pytest.raises(IngestPipelineError):
            ingestion_service.update_document(
                created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
            )
        assert chunk_store.count_by_document_id(created.document_id) == prior_count
