"""ING-* and META-ING-* security tests."""

from __future__ import annotations

import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.ingestion.errors import (
    IngestAuthzDeniedError,
    IngestUnauthorizedError,
    IngestValidationError,
)
from tests.rag.conftest import make_ingest_request


@pytest.mark.security
class TestIngestionAuthorization:
    def test_ing_001_valid_scope(self, ingestion_service, tenant_ids, request_id, chunk_store):
        request = make_ingest_request(tenant_ids)
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        assert response.http_status == 202
        assert response.chunk_count > 0
        assert chunk_store.count_by_document_id(response.document_id) == response.chunk_count

    def test_ing_002_cross_department_denied(
        self, ingestion_service, tenant_ids, request_id, document_store, chunk_store
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert document_store.count() == 0
        assert sum(chunk_store.count_by_document_id(d.id) for d in document_store.list_all()) == 0

    def test_ing_003_cross_company_denied(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(
            tenant_ids, company_key="C2", department_key="C2_D1"
        )
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert document_store.count() == 0

    def test_ing_004_u2_allowed_department(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D3")
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U2"]
        )
        assert response.http_status == 202
        assert chunk_store.count_by_document_id(response.document_id) > 0

    def test_ing_005_u2_unallowed_department(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U2"]
            )
        assert document_store.count() == 0

    def test_ing_006_empty_departments_denied(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(tenant_ids)
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U3"]
            )
        assert document_store.count() == 0

    def test_ing_007_company_wide_service(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["S1"]
        )
        assert response.http_status == 202
        assert chunk_store.count_by_document_id(response.document_id) > 0

    def test_ing_008_company_wide_cross_company(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(
            tenant_ids, company_key="C2", department_key="C2_D1"
        )
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["S1"]
            )
        assert document_store.count() == 0

    def test_ing_009_invalid_token(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(tenant_ids)
        with pytest.raises(IngestUnauthorizedError) as exc:
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["INVALID"]
            )
        assert exc.value.http_status == 401
        assert document_store.count() == 0

    def test_ing_010_no_auth(self, ingestion_service, tenant_ids, request_id, document_store):
        request = make_ingest_request(tenant_ids)
        with pytest.raises(IngestUnauthorizedError) as exc:
            ingestion_service.create_document(request, request_id, None)
        assert exc.value.http_status == 401
        assert document_store.count() == 0


@pytest.mark.security
class TestIngestionMetadataForgery:
    def test_meta_ing_001_forged_company_id(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(
            tenant_ids, company_key="C2", department_key="C2_D1"
        )
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert document_store.count() == 0

    def test_meta_ing_002_valid_scope_stored(
        self, ingestion_service, tenant_ids, request_id, document_store, chunk_store
    ):
        request = make_ingest_request(tenant_ids)
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        document = document_store.get(response.document_id)
        assert document is not None
        assert document.company_id == tenant_ids["companies"]["C1"]
        assert document.department_id == tenant_ids["departments"]["C1_D1"]
        chunks = chunk_store.list_by_document_id(response.document_id)
        for chunk in chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
            assert chunk.department_id == tenant_ids["departments"]["C1_D1"]

    def test_meta_ing_003_department_not_in_company(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(
            tenant_ids,
            company_key="C1",
            department_key="C2_D1",
        )
        with pytest.raises(IngestValidationError) as exc:
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert exc.value.http_status == 400
        assert document_store.count() == 0

    def test_meta_ing_005_server_assigned_chunk_ids(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        request = make_ingest_request(tenant_ids)
        response = ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        chunks = chunk_store.list_by_document_id(response.document_id)
        chunk_ids = {chunk.chunk_id for chunk in chunks}
        assert len(chunk_ids) == len(chunks)
        assert all(chunk.chunk_id for chunk in chunks)


@pytest.mark.security
class TestIngestionDisabledUser:
    def test_disabled_user_denied(
        self, ingestion_service, tenant_ids, request_id, document_store
    ):
        request = make_ingest_request(tenant_ids)
        with pytest.raises(IngestAuthzDeniedError) as exc:
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U_DISABLED"]
            )
        assert exc.value.http_status == 403
        assert document_store.count() == 0
