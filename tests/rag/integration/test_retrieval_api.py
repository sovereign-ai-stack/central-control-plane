"""Integration tests for the retrieval application/API boundary."""

from __future__ import annotations

from uuid import uuid4

import pytest
from tests.rag.conftest import make_ingest_request

from rag.app.errors import ApiValidationError
from rag.app.types import RetrievalApiRequest


class TestRetrievalApplicationIntegration:
    def test_basic_retrieval_ranks_relevant_document(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="سیاست مرخصی: مرخصی سالانه برای کارکنان ۲۶ روز است.",
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="راهنمای فنی سرور: پورت 8080 برای health check.",
                document_id=uuid4(),
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )

        response = retrieve_handler.retrieve(
            RetrievalApiRequest(
                query="مرخصی سالانه",
                request_id=request_id,
                top_k=5,
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count >= 1
        assert "مرخصی" in response.chunks[0].content
        assert response.chunks[0].score > response.chunks[-1].score or response.chunk_count == 1

    def test_top_k_values(self, rag_application, tenant_ids, request_id, retrieve_handler):
        for index in range(3):
            rag_application.ingestion_service.create_document(
                make_ingest_request(
                    tenant_ids,
                    content=f"سند top-k شماره {index}",
                    document_id=uuid4(),
                ),
                request_id,
                tenant_ids["tokens"]["U1"],
            )

        for top_k in (1, 3, 5):
            response = retrieve_handler.retrieve(
                RetrievalApiRequest(
                    query="سند top-k",
                    request_id=request_id,
                    top_k=top_k,
                ),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
            assert len(response.chunks) <= top_k

    def test_invalid_top_k_rejected(self, tenant_ids, request_id, retrieve_handler):
        with pytest.raises(ApiValidationError):
            retrieve_handler.retrieve(
                RetrievalApiRequest(
                    query="valid query",
                    request_id=request_id,
                    top_k=0,
                ),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_empty_query_rejected(self, tenant_ids, request_id, retrieve_handler):
        with pytest.raises(ApiValidationError):
            retrieve_handler.retrieve(
                RetrievalApiRequest(query="   ", request_id=request_id),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_no_results_returns_empty(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        response = retrieve_handler.retrieve(
            RetrievalApiRequest(
                query="هیچ سندی با این متن وجود ندارد",
                request_id=request_id,
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()
        assert response.chunk_count == 0

    def test_http_router_success(self, rag_application, tenant_ids, request_id, rag_http_app):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="HTTP router retrieval test"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/retrieve",
            {
                "query": "HTTP router retrieval test",
                "request_id": str(request_id),
                "top_k": 3,
            },
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 200
        assert body["retrieval"]["chunk_count"] >= 1
        assert "embedding" not in str(body)

    def test_end_to_end_ingest_then_retrieve(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="E2E marker: ingest embed persist retrieve",
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert rag_application.chunk_store.count_by_document_id(created.document_id) > 0

        response = retrieve_handler.retrieve(
            RetrievalApiRequest(
                query="E2E marker ingest embed persist retrieve",
                request_id=request_id,
                top_k=1,
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks
        assert response.chunks[0].document_id == created.document_id
