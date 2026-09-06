"""Security tests for the retrieval application/API boundary."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import pytest

from rag.app.errors import ApiAuthenticationError, ApiValidationError
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.types import RetrievalApiRequest
from rag.embedding.service import EmbeddingService
from rag.embedding.types import EmbeddingResult, QueryEmbeddingResult
from tests.rag.conftest import make_embedded_stored_chunk, make_ingest_request


class CountingEmbeddingService(EmbeddingService):
    def __init__(self, inner: EmbeddingService) -> None:
        self._inner = inner
        self.query_calls = 0

    @property
    def model(self):
        return self._inner.model

    @property
    def model_info(self):
        return self._inner.model_info

    def embed_query(self, raw_text: str) -> QueryEmbeddingResult:
        self.query_calls += 1
        return self._inner.embed_query(raw_text)

    def embed_documents(self, raw_texts: Sequence[str]) -> EmbeddingResult:
        return self._inner.embed_documents(raw_texts)

    def health_check(self) -> bool:
        return self._inner.health_check()


@pytest.fixture
def counting_retrieve_handler(rag_application):
    inner = rag_application.embedding_service
    counter = CountingEmbeddingService(inner)
    from rag.retrieval.engine import SecureRetrievalEngine

    engine = SecureRetrievalEngine(
        counter,
        rag_application.chunk_store,
        rag_application.document_store,
        rag_application.retrieval_metrics,
    )
    from rag.retrieval.service import RetrievalService

    service = RetrievalService(rag_application.identity_service, engine)
    return RetrieveHandler(service), counter


def _request(query: str, request_id, top_k: int = 5) -> RetrievalApiRequest:
    return RetrievalApiRequest(query=query, request_id=request_id, top_k=top_k)


@pytest.mark.security
class TestRetrievalApiSecurity:
    def test_unauthenticated_request_rejected(self, counting_retrieve_handler, request_id):
        handler, counter = counting_retrieve_handler
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(_request("secret", request_id), bearer_token=None)
        assert counter.query_calls == 0

    def test_invalid_token_rejected(
        self, counting_retrieve_handler, tenant_ids, request_id
    ):
        handler, counter = counting_retrieve_handler
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                _request("secret", request_id),
                bearer_token=tenant_ids["tokens"]["INVALID"],
            )
        assert counter.query_calls == 0

    def test_expired_token_rejected(
        self, counting_retrieve_handler, tenant_ids, request_id
    ):
        handler, counter = counting_retrieve_handler
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                _request("secret", request_id),
                bearer_token=tenant_ids["tokens"]["EXPIRED"],
            )
        assert counter.query_calls == 0

    def test_revoked_token_rejected(
        self, counting_retrieve_handler, tenant_ids, request_id
    ):
        handler, counter = counting_retrieve_handler
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                _request("secret", request_id),
                bearer_token=tenant_ids["tokens"]["REVOKED"],
            )
        assert counter.query_calls == 0

    def test_disabled_user_rejected(
        self, counting_retrieve_handler, tenant_ids, request_id
    ):
        handler, counter = counting_retrieve_handler
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                _request("secret", request_id),
                bearer_token=tenant_ids["tokens"]["U_DISABLED"],
            )
        assert counter.query_calls == 0

    def test_empty_department_scope_skips_embedding(
        self, counting_retrieve_handler, tenant_ids, request_id
    ):
        handler, counter = counting_retrieve_handler
        response = handler.retrieve(
            _request("anything", request_id),
            bearer_token=tenant_ids["tokens"]["U3"],
        )
        assert response.chunks == ()
        assert counter.query_calls == 0

    def test_forged_top_level_scope_rejected(self, tenant_ids, request_id, retrieve_handler):
        with pytest.raises(ApiValidationError, match="authorization scope"):
            retrieve_handler.parse_request(
                {
                    "query": "secret",
                    "request_id": str(request_id),
                    "company_id": str(tenant_ids["companies"]["C2"]),
                }
            )

    def test_forged_department_scope_rejected(self, tenant_ids, request_id, retrieve_handler):
        with pytest.raises(ApiValidationError, match="authorization scope"):
            retrieve_handler.parse_request(
                {
                    "query": "secret",
                    "request_id": str(request_id),
                    "department_ids": [str(tenant_ids["departments"]["C1_D2"])],
                }
            )

    def test_cross_company_e2e_negative(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="C1 visible document"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        c2_doc = uuid4()
        c2 = tenant_ids["companies"]["C2"]
        c2_d1 = tenant_ids["departments"]["C2_D1"]
        rag_application.document_store.create_processing(
            company_id=c2,
            department_id=c2_d1,
            source="seed",
            language="fa",
            source_type="test",
            content_hash="c2-only",
            normalization_version="fa-norm-v1",
            document_id=c2_doc,
        )
        rag_application.document_store.mark_indexed(
            c2_doc, chunk_count=1, content_hash="c2-only"
        )
        chunk = make_embedded_stored_chunk(
            rag_application.embedding_service,
            chunk_id=uuid4(),
            document_id=c2_doc,
            company_id=c2,
            department_id=c2_d1,
            content="C2 secret semantic best match",
        )
        rag_application.chunk_store.replace_document_chunks(c2_doc, [chunk])

        response = retrieve_handler.retrieve(
            _request("C2 secret semantic best match", request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert all(
            chunk.company_id == tenant_ids["companies"]["C1"] for chunk in response.chunks
        )
        assert all("C2 secret" not in chunk.content for chunk in response.chunks)

    def test_department_isolation_via_api(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="department d2 secret via api",
                department_key="C1_D2",
            ),
            request_id,
            tenant_ids["tokens"]["S1"],
        )
        response = retrieve_handler.retrieve(
            _request("department d2 secret via api", request_id),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()

    def test_http_unauthenticated_returns_401(
        self, rag_http_app, tenant_ids, request_id
    ):
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/retrieve",
            {"query": "secret", "request_id": str(request_id)},
            authorization=None,
        )
        assert status == 401
        assert body["code"] == "API_AUTHENTICATION_ERROR"

    def test_response_never_contains_vectors(
        self, rag_application, tenant_ids, request_id, rag_http_app
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="vector leak test document"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/retrieve",
            {
                "query": "vector leak test document",
                "request_id": str(request_id),
            },
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 200
        serialized = str(body).lower()
        assert "ndarray" not in serialized
        assert "float32" not in serialized
        assert "embedding" not in serialized

    def test_shared_embedding_service_between_ingestion_and_retrieval(
        self, rag_application
    ):
        assert rag_application.ingestion_service._pipeline._embedding is rag_application.embedding_service
        assert (
            rag_application.retrieval_service._engine._embedding
            is rag_application.embedding_service
        )
