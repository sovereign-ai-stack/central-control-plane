"""Integration tests for embedding persistence during ingestion."""

from __future__ import annotations

import numpy as np
from tests.rag.conftest import make_ingest_request

from rag.ingestion.types import IngestDocumentUpdateRequest


class TestIngestionEmbeddingIntegration:
    def test_successful_ingestion_persists_embeddings(
        self, ingestion_service, tenant_ids, request_id, chunk_store, embedding_service
    ):
        response = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = chunk_store.list_by_document_id(response.document_id)
        assert chunks
        info = embedding_service.model_info
        for chunk in chunks:
            assert chunk.embedding is not None
            assert chunk.embedding.shape == (info.dimension,)
            assert chunk.embedding_model_id == info.model_id
            assert chunk.embedding_dimension == info.dimension

    def test_batch_embedding_matches_individual_vectors(
        self, ingestion_service, tenant_ids, request_id, chunk_store, embedding_service
    ):
        response = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = chunk_store.list_by_document_id(response.document_id)
        for chunk in chunks:
            expected = embedding_service.embed_documents([chunk.content]).vectors[0]
            assert np.allclose(chunk.embedding, expected)

    def test_update_recomputes_embeddings(
        self, ingestion_service, tenant_ids, request_id, chunk_store
    ):
        created = ingestion_service.create_document(
            make_ingest_request(tenant_ids),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        before = chunk_store.list_by_document_id(created.document_id)
        update = IngestDocumentUpdateRequest(
            content="متن کاملاً متفاوت برای بازنمایی embedding در به‌روزرسانی.",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        updated = ingestion_service.update_document(
            created.document_id, update, request_id, tenant_ids["tokens"]["U1"]
        )
        after = chunk_store.list_by_document_id(updated.document_id)
        assert before[0].content_hash != after[0].content_hash
        assert not np.allclose(before[0].embedding, after[0].embedding)
        assert updated.version == 2

    def test_deduplicate_skips_embedding(
        self, ingestion_service, tenant_ids, request_id, monkeypatch
    ):
        calls = {"count": 0}
        original = ingestion_service._pipeline._embedding.embed_documents

        def counting_embed(texts):
            calls["count"] += 1
            return original(texts)

        monkeypatch.setattr(
            ingestion_service._pipeline._embedding,
            "embed_documents",
            counting_embed,
        )
        request = make_ingest_request(tenant_ids, deduplicate=True)
        ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        ingestion_service.create_document(
            request, request_id, tenant_ids["tokens"]["U1"]
        )
        assert calls["count"] == 1
