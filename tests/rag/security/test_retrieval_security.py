"""Security regression tests for secure vector retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import numpy as np
import pytest

from rag.authorization.context import AuthorizationContext
from rag.authorization.errors import ClientScopeForgeryError
from rag.contracts.retrieval import RetrievalOptions
from rag.embedding.errors import EmbeddingInferenceError
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.embedding.types import EmbeddingResult, QueryEmbeddingResult
from rag.identity.errors import MissingIdentityError
from rag.ingestion.errors import IngestPipelineError
from rag.ingestion.types import DocumentStatus
from rag.retrieval.engine import SecureRetrievalEngine
from rag.retrieval.errors import (
    RetrievalDimensionMismatchError,
    RetrievalModelMismatchError,
)
from rag.retrieval.service import RetrievalService
from tests.rag.conftest import (
    make_embedded_stored_chunk,
    make_ingest_request,
)


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


class AlternateModelStub(StubEmbeddingModel):
    def __init__(self) -> None:
        super().__init__(dimension=384, model_id="other-model-v1")


class WrongDimensionStub(StubEmbeddingModel):
    def health_check(self) -> bool:
        return True

    def embed_query(self, text: str) -> QueryEmbeddingResult:
        result = super().embed_query(text)
        bad = np.zeros(128, dtype=np.float32)
        return QueryEmbeddingResult(
            vector=bad,
            model_info=result.model_info,
            latency_ms=result.latency_ms,
        )


@pytest.fixture
def counting_retrieval_engine(
    embedding_service,
    chunk_store,
    document_store,
) -> tuple[SecureRetrievalEngine, CountingEmbeddingService]:
    counter = CountingEmbeddingService(embedding_service)
    engine = SecureRetrievalEngine(counter, chunk_store, document_store)
    return engine, counter


@pytest.fixture
def counting_retrieval_service(
    identity_service,
    counting_retrieval_engine,
) -> tuple[RetrievalService, CountingEmbeddingService]:
    engine, counter = counting_retrieval_engine
    return RetrievalService(identity_service, engine), counter


def _authz_u1_d1(tenant_ids, request_id) -> AuthorizationContext:
    return AuthorizationContext(
        user_id=tenant_ids["users"]["U1"],
        company_id=tenant_ids["companies"]["C1"],
        allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
        request_id=request_id,
    )


@pytest.mark.security
class TestRetrievalSecurity:
    def test_authorized_retrieval(
        self, ingestion_service, retrieval_engine, tenant_ids, request_id
    ):
        ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="authorized retrieval doc"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        result = retrieval_engine.search(
            "authorized retrieval doc",
            _authz_u1_d1(tenant_ids, request_id),
            RetrievalOptions(top_k=3),
        )
        assert len(result.chunks) >= 1

    def test_cross_company_isolation(
        self,
        ingestion_service,
        retrieval_engine,
        tenant_ids,
        request_id,
        document_store,
        chunk_store,
        embedding_service,
    ):
        ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="company c1 secret"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        c2_doc = uuid4()
        c2 = tenant_ids["companies"]["C2"]
        c2_d1 = tenant_ids["departments"]["C2_D1"]
        document_store.create_processing(
            company_id=c2,
            department_id=c2_d1,
            source="seed",
            language="fa",
            source_type="test",
            content_hash="c2-hash",
            normalization_version="fa-norm-v1",
            document_id=c2_doc,
        )
        document_store.mark_indexed(c2_doc, chunk_count=1, content_hash="c2-hash")
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=c2_doc,
            company_id=c2,
            department_id=c2_d1,
            content="company c2 secret",
        )
        chunk_store.replace_document_chunks(c2_doc, [chunk])

        result = retrieval_engine.search(
            "secret",
            _authz_u1_d1(tenant_ids, request_id),
            RetrievalOptions(top_k=10),
        )
        for item in result.chunks:
            assert item.company_id == tenant_ids["companies"]["C1"]
            assert "c2 secret" not in item.content

    def test_department_isolation(
        self, ingestion_service, retrieval_engine, tenant_ids, request_id
    ):
        ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="department d2 secret",
                department_key="C1_D2",
            ),
            request_id,
            tenant_ids["tokens"]["S1"],
        )
        result = retrieval_engine.search(
            "department d2 secret",
            _authz_u1_d1(tenant_ids, request_id),
            RetrievalOptions(top_k=5),
        )
        assert result.chunks == ()

    def test_unauthorized_request_skips_query_embedding(
        self, counting_retrieval_service, request_id
    ):
        service, counter = counting_retrieval_service
        with pytest.raises(MissingIdentityError):
            service.search("secret query", request_id, bearer_token=None)
        assert counter.query_calls == 0

    def test_missing_authz_skips_query_embedding(
        self, counting_retrieval_engine, request_id
    ):
        engine, counter = counting_retrieval_engine
        from rag.authorization.errors import MissingAuthorizationContextError

        with pytest.raises(MissingAuthorizationContextError):
            engine.search("secret query")
        assert counter.query_calls == 0

    def test_deleted_document_not_retrievable(
        self, ingestion_service, retrieval_engine, tenant_ids, request_id
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="delete me retrieval"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["U1"]
        )
        result = retrieval_engine.search(
            "delete me retrieval",
            _authz_u1_d1(tenant_ids, request_id),
        )
        assert result.chunks == ()

    def test_failed_ingestion_not_retrievable(
        self,
        ingestion_service,
        retrieval_engine,
        tenant_ids,
        request_id,
        chunk_store,
        document_store,
    ):
        from rag.embedding.service import EmbeddingService as ES
        from rag.ingestion.pipeline import IngestionPipeline
        from rag.ingestion.service import IngestionService

        class FailingStub(StubEmbeddingModel):
            def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
                raise EmbeddingInferenceError("simulated failure")

        failing_service = ES(FailingStub(), EmbeddingPreprocessor())
        pipeline = IngestionPipeline(
            document_store,
            chunk_store,
            failing_service,
            ingestion_service._pipeline.audit_log,
        )
        service = IngestionService(
            ingestion_service._identity,
            ingestion_service._authz,
            pipeline,
            document_store,
            chunk_store,
        )
        with pytest.raises(IngestPipelineError):
            service.create_document(
                make_ingest_request(tenant_ids, content="failed ingest retrieval"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        documents = document_store.list_all()
        assert documents[0].status == DocumentStatus.FAILED
        assert chunk_store.count_by_document_id(documents[0].id) == 0

        result = retrieval_engine.search(
            "failed ingest retrieval",
            _authz_u1_d1(tenant_ids, request_id),
        )
        assert result.chunks == ()

    def test_update_replaces_stale_vectors(
        self, ingestion_service, retrieval_engine, tenant_ids, request_id
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="old-vector-marker"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        from rag.ingestion.types import IngestDocumentUpdateRequest

        update = IngestDocumentUpdateRequest(
            content="new-vector-marker updated",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        ingestion_service.update_document(
            created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
        )
        result = retrieval_engine.search(
            "new-vector-marker",
            _authz_u1_d1(tenant_ids, request_id),
        )
        assert result.chunks
        assert all("new-vector-marker" in chunk.content for chunk in result.chunks)

    def test_dimension_mismatch_fails(
        self,
        chunk_store,
        document_store,
        tenant_ids,
        request_id,
        embedding_service,
    ):
        doc_id = uuid4()
        document_store.create_processing(
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            source="seed",
            language="fa",
            source_type="test",
            content_hash="dim-hash",
            normalization_version="fa-norm-v1",
            document_id=doc_id,
        )
        document_store.mark_indexed(doc_id, chunk_count=1, content_hash="dim-hash")
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=doc_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="dimension test chunk",
        )
        chunk_store.replace_document_chunks(doc_id, [chunk])

        bad_engine = SecureRetrievalEngine(
            EmbeddingService(WrongDimensionStub(), EmbeddingPreprocessor()),
            chunk_store,
            document_store,
        )
        with pytest.raises(RetrievalDimensionMismatchError):
            bad_engine.search(
                "dimension test chunk",
                _authz_u1_d1(tenant_ids, request_id),
            )

    def test_model_mismatch_fails(
        self,
        chunk_store,
        document_store,
        tenant_ids,
        request_id,
        embedding_service,
    ):
        doc_id = uuid4()
        document_store.create_processing(
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            source="seed",
            language="fa",
            source_type="test",
            content_hash="model-hash",
            normalization_version="fa-norm-v1",
            document_id=doc_id,
        )
        document_store.mark_indexed(doc_id, chunk_count=1, content_hash="model-hash")
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=doc_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="model mismatch chunk",
        )
        chunk_store.replace_document_chunks(doc_id, [chunk])

        alt_engine = SecureRetrievalEngine(
            EmbeddingService(AlternateModelStub(), EmbeddingPreprocessor()),
            chunk_store,
            document_store,
        )
        with pytest.raises(RetrievalModelMismatchError):
            alt_engine.search(
                "model mismatch chunk",
                _authz_u1_d1(tenant_ids, request_id),
            )

    def test_top_k_ranking_is_stable(
        self, ingestion_service, retrieval_engine, tenant_ids, request_id
    ):
        ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="stable ranking alpha"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="stable ranking beta",
                document_id=uuid4(),
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        authz = _authz_u1_d1(tenant_ids, request_id)
        first = retrieval_engine.search(
            "stable ranking alpha", authz, RetrievalOptions(top_k=2)
        )
        second = retrieval_engine.search(
            "stable ranking alpha", authz, RetrievalOptions(top_k=2)
        )
        assert [chunk.chunk_id for chunk in first.chunks] == [
            chunk.chunk_id for chunk in second.chunks
        ]
        assert first.chunks[0].score >= first.chunks[1].score

    def test_scope_forgery_still_rejected_on_ingest(
        self, ingestion_service, tenant_ids, request_id
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        with pytest.raises(ClientScopeForgeryError):
            ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
