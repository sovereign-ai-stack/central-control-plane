"""Unit tests for ingestion embedding integration."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import numpy as np
import pytest

from rag.embedding.errors import EmbeddingInferenceError
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.embedding.types import EmbeddingResult
from rag.ingestion.embedding_integration import embed_and_attach_chunks
from rag.ingestion.errors import IngestEmbeddingError
from rag.ingestion.types import StoredChunk
from rag.ingestion.validation import chunk_content_hash


def _draft(content: str, *, chunk_index: int = 0) -> StoredChunk:
    doc_id = uuid4()
    company_id = uuid4()
    department_id = uuid4()
    return StoredChunk(
        chunk_id=uuid4(),
        document_id=doc_id,
        company_id=company_id,
        department_id=department_id,
        document_version=1,
        chunk_index=chunk_index,
        content=content,
        content_hash=chunk_content_hash(content),
    )


class WrongShapeStub(StubEmbeddingModel):
    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        result = super().embed_documents(texts)
        bad = [np.zeros(128, dtype=np.float32) for _ in result.vectors]
        return EmbeddingResult(
            vectors=bad,
            model_info=result.model_info,
            latency_ms=result.latency_ms,
            batch_size=result.batch_size,
        )


class FailingStub(StubEmbeddingModel):
    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        raise EmbeddingInferenceError("simulated inference failure")


@pytest.fixture
def service() -> EmbeddingService:
    return EmbeddingService(StubEmbeddingModel(), EmbeddingPreprocessor())


class TestEmbedAndAttachChunks:
    def test_attaches_model_metadata(self, service: EmbeddingService) -> None:
        attached = embed_and_attach_chunks(service, [_draft("متن اول")])
        chunk = attached[0]
        assert chunk.embedding is not None
        assert chunk.embedding.shape == (384,)
        assert chunk.embedding_model_id == "stub-v1"
        assert chunk.embedding_dimension == 384

    def test_preserves_chunk_order(self, service: EmbeddingService) -> None:
        drafts = [_draft(f"chunk {index}", chunk_index=index) for index in range(3)]
        attached = embed_and_attach_chunks(service, drafts)
        assert [chunk.chunk_index for chunk in attached] == [0, 1, 2]
        assert [chunk.chunk_id for chunk in attached] == [draft.chunk_id for draft in drafts]

    def test_embedding_failure_raises_typed_error(self) -> None:
        service = EmbeddingService(FailingStub(), EmbeddingPreprocessor())
        with pytest.raises(IngestEmbeddingError, match="document embedding failed"):
            embed_and_attach_chunks(service, [_draft("fail me")])

    def test_wrong_dimension_raises(self) -> None:
        service = EmbeddingService(WrongShapeStub(), EmbeddingPreprocessor())
        with pytest.raises(IngestEmbeddingError, match="dimension mismatch"):
            embed_and_attach_chunks(service, [_draft("bad dim")])

    def test_count_mismatch_raises(self, service: EmbeddingService, monkeypatch) -> None:
        stub = service.model
        original_embed = stub.embed_documents

        def short_batch(_texts: Sequence[str]) -> EmbeddingResult:
            single = original_embed(["only one"])
            return EmbeddingResult(
                vectors=single.vectors,
                model_info=single.model_info,
                latency_ms=single.latency_ms,
                batch_size=1,
            )

        monkeypatch.setattr(stub, "embed_documents", short_batch)
        with pytest.raises(IngestEmbeddingError, match="count mismatch"):
            embed_and_attach_chunks(service, [_draft("a"), _draft("b", chunk_index=1)])
