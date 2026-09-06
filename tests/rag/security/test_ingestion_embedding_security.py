"""Security and failure tests for ingestion embedding integration."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import numpy as np
import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.embedding.errors import EmbeddingInferenceError
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.embedding.types import EmbeddingResult
from rag.ingestion.errors import IngestPipelineError
from rag.ingestion.types import DocumentStatus, IngestDocumentUpdateRequest
from rag.storage.chunk_store import InMemoryChunkStore
from tests.rag.conftest import SAMPLE_PERSIAN_CONTENT, make_ingest_request


class CountingStub(StubEmbeddingModel):
    def __init__(self) -> None:
        super().__init__()
        self.document_calls = 0

    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        self.document_calls += 1
        return super().embed_documents(texts)


class FailingStub(StubEmbeddingModel):
    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        raise EmbeddingInferenceError("simulated embedding failure")


@pytest.fixture
def counting_embedding_service() -> EmbeddingService:
    return EmbeddingService(CountingStub(), EmbeddingPreprocessor())


@pytest.fixture
def counting_pipeline(
    document_store,
    chunk_store,
    counting_embedding_service,
    audit_log,
):
    from rag.ingestion.pipeline import IngestionPipeline

    return IngestionPipeline(
        document_store, chunk_store, counting_embedding_service, audit_log
    )


@pytest.fixture
def counting_ingestion_service(
    identity_service,
    ingest_authz,
    counting_pipeline,
    document_store,
    chunk_store,
):
    from rag.ingestion.service import IngestionService

    return IngestionService(
        identity_service,
        ingest_authz,
        counting_pipeline,
        document_store,
        chunk_store,
    )


@pytest.mark.security
class TestIngestionEmbeddingSecurity:
    def test_authz_failure_does_not_invoke_embedding(
        self, counting_ingestion_service, tenant_ids, request_id, counting_embedding_service
    ):
        request = make_ingest_request(tenant_ids, department_key="C1_D2")
        with pytest.raises(ClientScopeForgeryError):
            counting_ingestion_service.create_document(
                request, request_id, tenant_ids["tokens"]["U1"]
            )
        assert counting_embedding_service.model.document_calls == 0

    def test_embedding_failure_leaves_no_orphan_chunks(
        self,
        identity_service,
        ingest_authz,
        document_store,
        chunk_store,
        audit_log,
        tenant_ids,
        request_id,
    ):
        from rag.ingestion.pipeline import IngestionPipeline
        from rag.ingestion.service import IngestionService

        failing_service = EmbeddingService(FailingStub(), EmbeddingPreprocessor())
        pipeline = IngestionPipeline(
            document_store, chunk_store, failing_service, audit_log
        )
        service = IngestionService(
            identity_service, ingest_authz, pipeline, document_store, chunk_store
        )
        with pytest.raises(IngestPipelineError):
            service.create_document(
                make_ingest_request(tenant_ids),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        documents = document_store.list_all()
        assert len(documents) == 1
        assert documents[0].status == DocumentStatus.FAILED
        assert chunk_store.count_by_document_id(documents[0].id) == 0
        assert len(chunk_store._chunks) == 0

    def test_tenant_chunks_remain_isolated(
        self,
        ingestion_service,
        tenant_ids,
        request_id,
        chunk_store,
        document_store,
        embedding_service,
    ):

        from tests.rag.conftest import make_embedded_stored_chunk

        c1_doc = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        c2_doc_id = uuid4()
        c2 = tenant_ids["companies"]["C2"]
        c2_d1 = tenant_ids["departments"]["C2_D1"]
        document_store.create_processing(
            company_id=c2,
            department_id=c2_d1,
            source="seed",
            language="fa",
            source_type="test",
            content_hash="tenant-c2-hash",
            normalization_version="fa-norm-v1",
            document_id=c2_doc_id,
        )
        document_store.mark_indexed(c2_doc_id, chunk_count=1, content_hash="tenant-c2-hash")
        c2_chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=c2_doc_id,
            company_id=c2,
            department_id=c2_d1,
            content="tenant c2 isolated content",
        )
        chunk_store.replace_document_chunks(c2_doc_id, [c2_chunk])

        c1_chunks = chunk_store.list_by_document_id(c1_doc.document_id)
        c2_chunks = chunk_store.list_by_document_id(c2_doc_id)
        assert c1_chunks
        assert c2_chunks
        for chunk in c1_chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
        for chunk in c2_chunks:
            assert chunk.company_id == tenant_ids["companies"]["C2"]
        assert {chunk.chunk_id for chunk in c1_chunks}.isdisjoint(
            {chunk.chunk_id for chunk in c2_chunks}
        )

    def test_chunk_store_rejects_missing_embedding(self, tenant_ids):

        from rag.ingestion.types import StoredChunk
        from rag.ingestion.validation import chunk_content_hash

        store = InMemoryChunkStore()
        doc_id = uuid4()
        chunk = StoredChunk(
            chunk_id=uuid4(),
            document_id=doc_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            document_version=1,
            chunk_index=0,
            content="no embedding",
            content_hash=chunk_content_hash("no embedding"),
        )
        with pytest.raises(ValueError, match="missing embedding metadata"):
            store.replace_document_chunks(doc_id, [chunk])

    def test_update_failure_preserves_prior_embeddings(
        self,
        ingestion_service,
        tenant_ids,
        request_id,
        chunk_store,
        monkeypatch,
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        before = chunk_store.list_by_document_id(created.document_id)
        chunk_store.set_fail_on_write(True)
        update = IngestDocumentUpdateRequest(
            content=SAMPLE_PERSIAN_CONTENT + " update that fails",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        with pytest.raises(IngestPipelineError):
            ingestion_service.update_document(
                created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
            )
        after = chunk_store.list_by_document_id(created.document_id)
        assert len(after) == len(before)
        for old, current in zip(before, after, strict=True):
            assert old.chunk_id == current.chunk_id
            assert np.allclose(old.embedding, current.embedding)
