"""
Backend-agnostic `ChunkStore` conformance suite.

Every requirement here is stated against the protocol, never against
`InMemoryChunkStore`. A production adapter (Weaviate) must pass this suite
unchanged — see `specs/000-system-architecture/storage-extension.md`.

To certify a new adapter, add it to the `chunk_store_factory` fixture params.
"""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest
from tests.rag.conftest import make_embedded_stored_chunk
from tests.rag.storage_support import (
    unique_collection_name,
    weaviate_available_for_tests,
    weaviate_config,
)

from rag.retrieval.errors import (
    RetrievalDimensionMismatchError,
    RetrievalModelMismatchError,
)
from rag.storage.chunk_store import ChunkStore, InMemoryChunkStore
from rag.storage.vector_search import ScoredChunk, VectorSearchScope

# Every registered backend must satisfy the identical contract below. The
# Weaviate backend participates only when a real instance is configured; the
# suite still runs fully in-memory otherwise.
BACKENDS = ["in_memory"]
if weaviate_available_for_tests():
    BACKENDS.append("weaviate")


@pytest.fixture(params=BACKENDS, ids=BACKENDS)
def store(request) -> ChunkStore:
    if request.param == "in_memory":
        return InMemoryChunkStore()

    from rag.storage.weaviate.store import WeaviateChunkStore

    name = unique_collection_name("Contract")
    backend = WeaviateChunkStore(weaviate_config(name))

    def cleanup() -> None:
        try:
            backend.client.collections.delete(name)
        finally:
            backend.close()

    request.addfinalizer(cleanup)
    return backend


@pytest.fixture
def seeded(store, embedding_service, tenant_ids):
    """Two companies, three departments, one document each."""
    c1 = tenant_ids["companies"]["C1"]
    c2 = tenant_ids["companies"]["C2"]
    d1 = tenant_ids["departments"]["C1_D1"]
    d2 = tenant_ids["departments"]["C1_D2"]
    c2d1 = tenant_ids["departments"]["C2_D1"]

    records = {}
    for key, company_id, department_id, content in (
        ("c1d1", c1, d1, "سند اول شرکت یک بخش یک"),
        ("c1d2", c1, d2, "سند دوم شرکت یک بخش دو"),
        ("c2d1", c2, c2d1, "سند سوم شرکت دو بخش یک"),
    ):
        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=company_id,
            department_id=department_id,
            content=content,
        )
        store.replace_document_chunks(document_id, [chunk])
        records[key] = (document_id, chunk)
    return records


def _scope(tenant_ids, seeded, *, company="C1", departments=("C1_D1",), docs=None):
    if docs is None:
        docs = [seeded["c1d1"][0]]
    return VectorSearchScope(
        company_id=tenant_ids["companies"][company],
        allowed_department_ids=tuple(
            tenant_ids["departments"][name] for name in departments
        ),
        allowed_document_ids=frozenset(docs),
    )


def _query(embedding_service, text: str):
    result = embedding_service.embed_query(text)
    return result.vector, result.model_info.model_id, result.model_info.dimension


class TestProtocolConformance:
    def test_store_satisfies_the_protocol(self, store):
        assert isinstance(store, ChunkStore)

    def test_write_then_count_and_list(self, store, seeded):
        document_id, chunk = seeded["c1d1"]
        assert store.count_by_document_id(document_id) == 1
        listed = store.list_by_document_id(document_id)
        assert [item.chunk_id for item in listed] == [chunk.chunk_id]

    def test_replace_is_idempotent_on_the_document(
        self, store, seeded, embedding_service, tenant_ids
    ):
        document_id, _ = seeded["c1d1"]
        replacement = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="محتوای جایگزین",
        )
        store.replace_document_chunks(document_id, [replacement])
        assert store.count_by_document_id(document_id) == 1
        assert store.list_by_document_id(document_id)[0].chunk_id == replacement.chunk_id

    def test_delete_removes_all_document_chunks(self, store, seeded):
        document_id, _ = seeded["c1d1"]
        assert store.delete_by_document_id(document_id) == 1
        assert store.count_by_document_id(document_id) == 0
        assert store.list_by_document_id(document_id) == []

    def test_unknown_document_is_empty_not_an_error(self, store):
        unknown = uuid4()
        assert store.count_by_document_id(unknown) == 0
        assert store.list_by_document_id(unknown) == []

    def test_search_returns_scored_chunks_and_pool_size(
        self, store, seeded, embedding_service, tenant_ids
    ):
        vector, model_id, dimension = _query(embedding_service, "سند اول شرکت یک بخش یک")
        results, pool = store.search(
            vector,
            _scope(tenant_ids, seeded),
            top_k=5,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert pool >= 1
        assert all(isinstance(item, ScoredChunk) for item in results)
        assert results[0].chunk.content.startswith("سند اول")

    def test_top_k_truncates_but_pool_size_reports_the_full_match_count(
        self, store, seeded, embedding_service, tenant_ids
    ):
        document_ids = [seeded["c1d1"][0], seeded["c1d2"][0]]
        vector, model_id, dimension = _query(embedding_service, "سند")
        results, pool = store.search(
            vector,
            _scope(
                tenant_ids,
                seeded,
                departments=("C1_D1", "C1_D2"),
                docs=document_ids,
            ),
            top_k=1,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert len(results) == 1
        assert pool == 2


class TestScopeEnforcement:
    """ST-001..ST-006 — filtering must be part of the store query."""

    def test_company_isolation(self, store, seeded, embedding_service, tenant_ids):
        vector, model_id, dimension = _query(embedding_service, "سند سوم شرکت دو")
        # Scope is company C1 but the document belongs to C2.
        results, pool = store.search(
            vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C2_D1"],),
                allowed_document_ids=frozenset({seeded["c2d1"][0]}),
            ),
            top_k=5,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert results == []
        assert pool == 0

    def test_department_isolation(self, store, seeded, embedding_service, tenant_ids):
        vector, model_id, dimension = _query(embedding_service, "سند دوم شرکت یک بخش دو")
        results, pool = store.search(
            vector,
            _scope(tenant_ids, seeded, departments=("C1_D1",), docs=[seeded["c1d2"][0]]),
            top_k=5,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert results == []
        assert pool == 0

    def test_document_scope_is_enforced(
        self, store, seeded, embedding_service, tenant_ids
    ):
        vector, model_id, dimension = _query(embedding_service, "سند اول شرکت یک")
        results, _ = store.search(
            vector,
            _scope(tenant_ids, seeded, docs=[uuid4()]),
            top_k=5,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert results == []

    def test_empty_department_scope_returns_nothing(
        self, store, seeded, embedding_service, tenant_ids
    ):
        vector, model_id, dimension = _query(embedding_service, "سند")
        results, pool = store.search(
            vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(),
                allowed_document_ids=frozenset({seeded["c1d1"][0]}),
            ),
            top_k=5,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert results == []
        assert pool == 0

    def test_empty_document_scope_returns_nothing(
        self, store, seeded, embedding_service, tenant_ids
    ):
        vector, model_id, dimension = _query(embedding_service, "سند")
        results, pool = store.search(
            vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
                allowed_document_ids=frozenset(),
            ),
            top_k=5,
            query_model_id=model_id,
            query_dimension=dimension,
        )
        assert results == []
        assert pool == 0

    def test_search_requires_a_scope_argument(self, store, embedding_service):
        vector, model_id, dimension = _query(embedding_service, "سند")
        with pytest.raises(TypeError):
            store.search(  # type: ignore[call-arg]
                vector, top_k=5, query_model_id=model_id, query_dimension=dimension
            )


class TestVectorCompatibility:
    """ST-007/ST-008 — model and dimension mismatches must fail closed."""

    def test_model_mismatch_rejected(self, store, seeded, embedding_service, tenant_ids):
        vector, _model_id, dimension = _query(embedding_service, "سند اول")
        with pytest.raises(RetrievalModelMismatchError):
            store.search(
                vector,
                _scope(tenant_ids, seeded),
                top_k=5,
                query_model_id="some-other-model",
                query_dimension=dimension,
            )

    def test_query_dimension_mismatch_rejected(
        self, store, seeded, embedding_service, tenant_ids
    ):
        vector, model_id, dimension = _query(embedding_service, "سند اول")
        with pytest.raises(RetrievalDimensionMismatchError):
            store.search(
                vector,
                _scope(tenant_ids, seeded),
                top_k=5,
                query_model_id=model_id,
                query_dimension=dimension + 1,
            )

    def test_chunk_without_embedding_metadata_rejected_on_write(
        self, store, tenant_ids
    ):
        from rag.ingestion.types import StoredChunk

        document_id = uuid4()
        bare = StoredChunk(
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            document_version=1,
            chunk_index=0,
            content="بدون بردار",
            content_hash="hash",
        )
        with pytest.raises(ValueError):
            store.replace_document_chunks(document_id, [bare])

    def test_wrong_dtype_rejected_on_write(self, store, embedding_service, tenant_ids):
        from dataclasses import replace

        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="متن",
        )
        broken = replace(chunk, embedding=chunk.embedding.astype(np.float64))
        with pytest.raises(ValueError):
            store.replace_document_chunks(document_id, [broken])


class TestWriteIntegrity:
    """ST-010 — a rejected write must not leave partial state."""

    def test_mixed_scope_batch_rejected(self, store, embedding_service, tenant_ids):
        document_id = uuid4()
        first = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="اول",
        )
        second = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D2"],
            content="دوم",
        )
        with pytest.raises(ValueError):
            store.replace_document_chunks(document_id, [first, second])
        assert store.count_by_document_id(document_id) == 0

    def test_document_id_mismatch_rejected(self, store, embedding_service, tenant_ids):
        document_id = uuid4()
        foreign = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=uuid4(),
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="ناهماهنگ",
        )
        with pytest.raises(ValueError):
            store.replace_document_chunks(document_id, [foreign])
        assert store.count_by_document_id(document_id) == 0

    def test_phase5_enrichment_fields_round_trip(
        self, store, embedding_service, tenant_ids
    ):
        from dataclasses import replace

        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="متن غنی‌شده",
        )
        enriched = replace(
            chunk,
            embedding_text="متن",
            nlp_version="fa-nlp-v1+fa-norm-v2+morph",
            language="fa",
            source_segment_label="page",
            source_segment_start=3,
            source_segment_end=3,
        )
        store.replace_document_chunks(document_id, [enriched])
        stored = store.list_by_document_id(document_id)[0]
        assert stored.nlp_version == "fa-nlp-v1+fa-norm-v2+morph"
        assert stored.source_segment_start == 3
        assert stored.language == "fa"
