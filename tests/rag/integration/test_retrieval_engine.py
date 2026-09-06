"""Integration tests for secure vector retrieval."""

from __future__ import annotations

from uuid import uuid4

import pytest
from tests.rag.conftest import make_ingest_request

from rag.authorization.context import AuthorizationContext
from rag.contracts.retrieval import RetrievalOptions, RetrievedChunk
from rag.ingestion.types import IngestDocumentUpdateRequest
from rag.retrieval.errors import RetrievalValidationError


class TestRetrievalIntegration:
    def test_ingested_document_is_retrievable(
        self,
        ingestion_service,
        retrieval_engine,
        tenant_ids,
        request_id,
    ):
        doc_content = "سند ویژه بازیابی: alpha-retrieval-marker"
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=doc_content),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        result = retrieval_engine.search(
            doc_content,
            authz,
            RetrievalOptions(top_k=5),
        )
        assert len(result.chunks) >= 1
        top = result.chunks[0]
        assert isinstance(top, RetrievedChunk)
        assert top.document_id == created.document_id
        assert "alpha-retrieval-marker" in top.content
        assert top.score > 0.9

    def test_top_k_limits_results(
        self,
        ingestion_service,
        retrieval_engine,
        tenant_ids,
        request_id,
    ):
        for marker in ("doc-a", "doc-b", "doc-c"):
            ingestion_service.create_document(
                make_ingest_request(
                    tenant_ids,
                    content=f"متن {marker} برای top-k",
                    document_id=uuid4(),
                ),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        result = retrieval_engine.search(
            "متن doc-b برای top-k",
            authz,
            RetrievalOptions(top_k=1),
        )
        assert len(result.chunks) == 1

    def test_empty_corpus_returns_empty(
        self,
        retrieval_engine,
        tenant_ids,
        request_id,
    ):
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        result = retrieval_engine.search("anything", authz)
        assert result.chunks == ()

    def test_invalid_top_k_rejected(self, retrieval_engine, tenant_ids, request_id):
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        with pytest.raises(RetrievalValidationError):
            retrieval_engine.search("query", authz, RetrievalOptions(top_k=0))

    def test_update_returns_new_content(
        self,
        ingestion_service,
        retrieval_engine,
        tenant_ids,
        request_id,
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="محتوای اولیه retrieval"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        update = IngestDocumentUpdateRequest(
            content="محتوای به‌روز شده retrieval marker-new",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        ingestion_service.update_document(
            created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
        )
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        result = retrieval_engine.search("marker-new", authz, RetrievalOptions(top_k=3))
        assert result.chunks
        assert all("marker-new" in chunk.content for chunk in result.chunks)
        assert all("محتوای اولیه" not in chunk.content for chunk in result.chunks)
