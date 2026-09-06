"""FUNC-ING-* functional integration tests."""

from __future__ import annotations

from uuid import UUID

import pytest
from tests.rag.conftest import SAMPLE_PERSIAN_CONTENT, make_ingest_request

from rag.ingestion.errors import IngestDuplicateError, IngestNotFoundError, IngestValidationError
from rag.ingestion.persian import normalize_persian
from rag.ingestion.types import DocumentStatus, IngestDocumentUpdateRequest


class TestIngestionPipelineFunctional:
    def test_func_ing_001_valid_ingestion(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        response = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert response.http_status == 202
        assert response.status == DocumentStatus.INDEXED
        assert response.chunk_count > 0
        document = document_store.get(response.document_id)
        assert document is not None
        assert document.content_hash == response.content_hash

    def test_func_ing_002_auto_document_id(self, ingestion_service, tenant_ids, request_id):
        response = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert isinstance(response.document_id, UUID)

    def test_func_ing_003_all_chunks_have_security_metadata(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        response = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        for chunk in chunk_store.list_by_document_id(response.document_id):
            assert chunk.chunk_id
            assert chunk.document_id
            assert chunk.company_id
            assert chunk.department_id

    def test_func_ing_004_persian_normalization_applied(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(
            tenant_ids, content="علي   كتاب\n\nجدید"
        )
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        document = document_store.get(response.document_id)
        assert document is not None
        assert document.normalization_version == "fa-norm-v1"
        expected_hash_source = normalize_persian("علي   كتاب\n\nجدید")
        from rag.ingestion.validation import content_hash

        assert document.content_hash == content_hash(expected_hash_source)

    def test_func_ing_005_deduplicate_returns_existing(
        self, ingestion_service, tenant_ids, request_id
    ):
        request = make_ingest_request(tenant_ids, deduplicate=True)
        first = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        second = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        assert second.http_status == 200
        assert second.deduplicated is True
        assert second.document_id == first.document_id

    def test_func_ing_006_duplicate_conflict(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(tenant_ids, deduplicate=False)
        ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        with pytest.raises(IngestDuplicateError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        indexed = [
            d for d in document_store.list_all() if d.status == DocumentStatus.INDEXED
        ]
        assert len(indexed) == 1

    def test_func_ing_007_empty_content_rejected(self, ingestion_service, tenant_ids, request_id):
        request = make_ingest_request(tenant_ids, content="  ")
        with pytest.raises(IngestValidationError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )

    def test_func_ing_008_department_not_in_company(
        self, ingestion_service, tenant_ids, request_id
    ):
        request = make_ingest_request(
            tenant_ids, company_key="C1", department_key="C2_D1"
        )
        with pytest.raises(IngestValidationError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )

    def test_func_ing_012_content_hash_in_response(
        self, ingestion_service, tenant_ids, request_id
    ):
        response = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert len(response.content_hash) == 64

    def test_update_increments_version(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        update = IngestDocumentUpdateRequest(
            content=SAMPLE_PERSIAN_CONTENT + " revised",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        updated = ingestion_service.update_document(
            created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
        )
        assert updated.version == created.version + 1
        document = document_store.get(updated.document_id)
        assert document is not None
        assert document.version == updated.version

    def test_func_del_003_delete_nonexistent(self, ingestion_service, tenant_ids, request_id):
        from uuid import uuid4

        with pytest.raises(IngestNotFoundError):
            ingestion_service.delete_document(
                uuid4(), request_id, tenant_ids["tokens"]["U1"]
            )
