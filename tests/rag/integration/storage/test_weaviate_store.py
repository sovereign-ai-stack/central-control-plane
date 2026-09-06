"""
Integration tests for `WeaviateChunkStore` against a real Weaviate (Phase 6).

Skipped unless `RAG_WEAVIATE_TEST_URL` is set. Start an instance with:

    docker compose -f docker-compose.weaviate.yml up -d
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import numpy as np
import pytest
from tests.rag.storage_support import (
    requires_weaviate,
    unique_collection_name,
    weaviate_config,
)

from rag.ingestion.types import StoredChunk
from rag.retrieval.errors import (
    RetrievalDimensionMismatchError,
    RetrievalModelMismatchError,
)
from rag.storage.errors import StorageScopeTooLargeError, StorageWriteError
from rag.storage.vector_search import VectorSearchScope

pytestmark = requires_weaviate

DIM = 8
MODEL = "stub-v1"


def unit_vector(seed: int, dim: int = DIM) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=dim).astype(np.float32)
    return vector / np.linalg.norm(vector)


def make_chunk(
    document_id,
    company_id,
    department_id,
    *,
    index: int = 0,
    seed: int = 0,
    content: str = "متن",
    model_id: str = MODEL,
    dimension: int = DIM,
    **extra,
) -> StoredChunk:
    return StoredChunk(
        chunk_id=uuid4(),
        document_id=document_id,
        company_id=company_id,
        department_id=department_id,
        document_version=1,
        chunk_index=index,
        content=content,
        content_hash=f"hash-{index}",
        embedding=unit_vector(seed, dimension),
        embedding_model_id=model_id,
        embedding_dimension=dimension,
        **extra,
    )


@pytest.fixture
def store():
    from rag.storage.weaviate.store import WeaviateChunkStore

    name = unique_collection_name("Integration")
    backend = WeaviateChunkStore(weaviate_config(name))
    yield backend
    try:
        backend.client.collections.delete(name)
    finally:
        backend.close()


@pytest.fixture
def tenants():
    return {
        "c1": uuid4(),
        "c2": uuid4(),
        "d1": uuid4(),
        "d2": uuid4(),
    }


def scope_for(company, departments, documents) -> VectorSearchScope:
    return VectorSearchScope(
        company_id=company,
        allowed_department_ids=tuple(departments),
        allowed_document_ids=frozenset(documents),
    )


class TestInsertAndFetch:
    def test_insert_then_count(self, store, tenants):
        document_id = uuid4()
        chunks = [
            make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=i)
            for i in range(4)
        ]
        store.replace_document_chunks(document_id, chunks)
        assert store.count_by_document_id(document_id) == 4

    def test_list_is_ordered_by_chunk_index(self, store, tenants):
        document_id = uuid4()
        chunks = [
            make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=i)
            for i in reversed(range(5))
        ]
        store.replace_document_chunks(document_id, chunks)
        listed = store.list_by_document_id(document_id)
        assert [c.chunk_index for c in listed] == [0, 1, 2, 3, 4]

    def test_all_metadata_round_trips(self, store, tenants):
        document_id = uuid4()
        chunk = make_chunk(
            document_id,
            tenants["c1"],
            tenants["d1"],
            content="محتوای اصلی",
            token_count=7,
            original_text="اصل",
            embedding_text="پردازش شده",
            nlp_version="fa-nlp-v1+fa-norm-v2+morph",
            language="fa",
            section_path="ماده ۵",
            char_start=12,
            char_end=99,
            source_segment_label="page",
            source_segment_start=2,
            source_segment_end=3,
        )
        store.replace_document_chunks(document_id, [chunk])
        stored = store.list_by_document_id(document_id)[0]
        assert stored.content == "محتوای اصلی"
        assert stored.content_hash == chunk.content_hash
        assert stored.nlp_version == "fa-nlp-v1+fa-norm-v2+morph"
        assert stored.source_segment_start == 2
        assert stored.language == "fa"
        assert stored.token_count == 7

    def test_embedding_round_trips_on_explicit_fetch(self, store, tenants):
        document_id = uuid4()
        chunk = make_chunk(document_id, tenants["c1"], tenants["d1"], seed=3)
        store.replace_document_chunks(document_id, [chunk])
        stored = store.list_by_document_id(document_id)[0]
        assert stored.embedding is not None
        assert np.allclose(stored.embedding, chunk.embedding, atol=1e-6)

    def test_unknown_document_is_empty(self, store):
        assert store.count_by_document_id(uuid4()) == 0
        assert store.list_by_document_id(uuid4()) == []


class TestVectorSearch:
    def test_identical_vector_scores_one(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [make_chunk(document_id, tenants["c1"], tenants["d1"], seed=1)],
        )
        results, pool = store.search(
            unit_vector(1),
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=5,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert pool == 1
        assert results[0].score == pytest.approx(1.0, abs=1e-5)

    def test_similarity_matches_cosine(self, store, tenants):
        document_id = uuid4()
        chunk = make_chunk(document_id, tenants["c1"], tenants["d1"], seed=7)
        store.replace_document_chunks(document_id, [chunk])
        query = unit_vector(11)
        expected = float(np.dot(query, chunk.embedding))
        results, _ = store.search(
            query,
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=1,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert results[0].score == pytest.approx(expected, abs=1e-4)

    def test_results_are_ordered_by_descending_score(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=i)
                for i in range(6)
            ],
        )
        results, _ = store.search(
            unit_vector(0),
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=6,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        scores = [item.score for item in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_limits_results_but_not_pool_size(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=i)
                for i in range(7)
            ],
        )
        results, pool = store.search(
            unit_vector(0),
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=3,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert len(results) == 3
        assert pool == 7

    def test_empty_corpus_returns_empty(self, store, tenants):
        results, pool = store.search(
            unit_vector(0),
            scope_for(tenants["c1"], [tenants["d1"]], [uuid4()]),
            top_k=5,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert results == []
        assert pool == 0

    def test_search_is_repeatable(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=i)
                for i in range(5)
            ],
        )
        scope = scope_for(tenants["c1"], [tenants["d1"]], [document_id])
        first, _ = store.search(
            unit_vector(2), scope, top_k=3, query_model_id=MODEL, query_dimension=DIM
        )
        second, _ = store.search(
            unit_vector(2), scope, top_k=3, query_model_id=MODEL, query_dimension=DIM
        )
        assert [c.chunk.chunk_id for c in first] == [c.chunk.chunk_id for c in second]

    def test_identical_scores_break_ties_by_chunk_id(self, store, tenants):
        """Duplicate vectors must order deterministically, as in-memory does."""
        document_id = uuid4()
        chunks = [
            make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=42)
            for i in range(4)
        ]
        store.replace_document_chunks(document_id, chunks)
        results, _ = store.search(
            unit_vector(42),
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=4,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        returned = [str(item.chunk.chunk_id) for item in results]
        assert returned == sorted(returned)


class TestModelCompatibility:
    def test_model_mismatch_raises(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id, tenants["c1"], tenants["d1"], model_id="other-model"
                )
            ],
        )
        with pytest.raises(RetrievalModelMismatchError):
            store.search(
                unit_vector(0),
                scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
                top_k=5,
                query_model_id=MODEL,
                query_dimension=DIM,
            )

    def test_stored_dimension_mismatch_raises(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [make_chunk(document_id, tenants["c1"], tenants["d1"], dimension=16)],
        )
        with pytest.raises(RetrievalDimensionMismatchError):
            store.search(
                unit_vector(0),
                scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
                top_k=5,
                query_model_id=MODEL,
                query_dimension=DIM,
            )

    def test_query_dimension_mismatch_raises(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id, [make_chunk(document_id, tenants["c1"], tenants["d1"])]
        )
        with pytest.raises(RetrievalDimensionMismatchError):
            store.search(
                unit_vector(0, dim=16),
                scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
                top_k=5,
                query_model_id=MODEL,
                query_dimension=DIM,
            )


class TestDocumentStatusGate:
    """Searchability comes from the denormalised status, filtered server-side."""

    def test_processing_chunks_are_not_searchable(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                replace(
                    make_chunk(document_id, tenants["c1"], tenants["d1"], seed=1),
                    document_status="processing",
                )
            ],
        )
        results, pool = store.search(
            unit_vector(1),
            VectorSearchScope(
                company_id=tenants["c1"], allowed_department_ids=(tenants["d1"],)
            ),
            top_k=10,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert results == []
        assert pool == 0

    def test_indexed_chunks_are_searchable_without_a_document_list(
        self, store, tenants
    ):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                replace(
                    make_chunk(document_id, tenants["c1"], tenants["d1"], seed=1),
                    document_status="indexed",
                )
            ],
        )
        results, pool = store.search(
            unit_vector(1),
            VectorSearchScope(
                company_id=tenants["c1"], allowed_department_ids=(tenants["d1"],)
            ),
            top_k=10,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert pool == 1
        assert len(results) == 1

    def test_set_document_status_publishes_chunks(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                replace(
                    make_chunk(
                        document_id, tenants["c1"], tenants["d1"], index=i, seed=i
                    ),
                    document_status="processing",
                )
                for i in range(3)
            ],
        )
        scope = VectorSearchScope(
            company_id=tenants["c1"], allowed_department_ids=(tenants["d1"],)
        )
        assert store.search(
            unit_vector(0), scope, top_k=10, query_model_id=MODEL, query_dimension=DIM
        ) == ([], 0)

        assert store.set_document_status(document_id, "indexed") == 3
        _results, pool = store.search(
            unit_vector(0), scope, top_k=10, query_model_id=MODEL, query_dimension=DIM
        )
        assert pool == 3

    def test_unpublishing_hides_chunks_again(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                replace(
                    make_chunk(document_id, tenants["c1"], tenants["d1"], seed=2),
                    document_status="indexed",
                )
            ],
        )
        scope = VectorSearchScope(
            company_id=tenants["c1"], allowed_department_ids=(tenants["d1"],)
        )
        assert store.search(
            unit_vector(2), scope, top_k=10, query_model_id=MODEL, query_dimension=DIM
        )[1] == 1

        store.set_document_status(document_id, "processing")
        assert store.search(
            unit_vector(2), scope, top_k=10, query_model_id=MODEL, query_dimension=DIM
        ) == ([], 0)

    def test_status_gate_does_not_bypass_company_isolation(self, store, tenants):
        """An INDEXED chunk in another tenant must still be invisible."""
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                replace(
                    make_chunk(document_id, tenants["c2"], tenants["d1"], seed=3),
                    document_status="indexed",
                )
            ],
        )
        results, pool = store.search(
            unit_vector(3),
            VectorSearchScope(
                company_id=tenants["c1"], allowed_department_ids=(tenants["d1"],)
            ),
            top_k=10,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert results == []
        assert pool == 0

    def test_no_document_id_ceiling_without_an_explicit_list(self, store, tenants):
        """The 4k scope cap does not apply when the status filter is used."""
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                replace(
                    make_chunk(document_id, tenants["c1"], tenants["d1"], seed=4),
                    document_status="indexed",
                )
            ],
        )
        store._config = replace(store.config, max_scope_document_ids=1)
        # No StorageScopeTooLargeError: no id list is sent at all.
        _results, pool = store.search(
            unit_vector(4),
            VectorSearchScope(
                company_id=tenants["c1"], allowed_department_ids=(tenants["d1"],)
            ),
            top_k=10,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert pool == 1


class TestUpdateAndDelete:
    def test_replacement_removes_stale_chunks(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id,
                    tenants["c1"],
                    tenants["d1"],
                    index=i,
                    seed=i,
                    content=f"نسخه اول {i}",
                )
                for i in range(3)
            ],
        )
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id,
                    tenants["c1"],
                    tenants["d1"],
                    seed=9,
                    content="نسخه دوم",
                )
            ],
        )
        assert store.count_by_document_id(document_id) == 1
        contents = [c.content for c in store.list_by_document_id(document_id)]
        assert contents == ["نسخه دوم"]

    def test_stale_chunks_are_not_searchable_after_update(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id,
                    tenants["c1"],
                    tenants["d1"],
                    seed=1,
                    content="STALE MARKER",
                )
            ],
        )
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id,
                    tenants["c1"],
                    tenants["d1"],
                    seed=1,
                    content="FRESH MARKER",
                )
            ],
        )
        results, _ = store.search(
            unit_vector(1),
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=10,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        contents = [item.chunk.content for item in results]
        assert "FRESH MARKER" in contents
        assert "STALE MARKER" not in contents

    def test_delete_removes_everything(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(document_id, tenants["c1"], tenants["d1"], index=i, seed=i)
                for i in range(3)
            ],
        )
        assert store.delete_by_document_id(document_id) == 3
        assert store.count_by_document_id(document_id) == 0

    def test_deleted_document_is_not_searchable(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id, tenants["c1"], tenants["d1"], content="DELETED BODY"
                )
            ],
        )
        store.delete_by_document_id(document_id)
        results, pool = store.search(
            unit_vector(0),
            scope_for(tenants["c1"], [tenants["d1"]], [document_id]),
            top_k=10,
            query_model_id=MODEL,
            query_dimension=DIM,
        )
        assert results == []
        assert pool == 0

    def test_replacing_with_empty_clears_the_document(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id, [make_chunk(document_id, tenants["c1"], tenants["d1"])]
        )
        store.replace_document_chunks(document_id, [])
        assert store.count_by_document_id(document_id) == 0

    def test_delete_is_scoped_to_one_document(self, store, tenants):
        keep = uuid4()
        drop = uuid4()
        store.replace_document_chunks(
            keep, [make_chunk(keep, tenants["c1"], tenants["d1"], content="KEEP")]
        )
        store.replace_document_chunks(
            drop, [make_chunk(drop, tenants["c1"], tenants["d1"], content="DROP")]
        )
        store.delete_by_document_id(drop)
        assert store.count_by_document_id(keep) == 1


class TestFailureAtomicity:
    def test_invalid_batch_writes_nothing(self, store, tenants):
        document_id = uuid4()
        good = make_chunk(document_id, tenants["c1"], tenants["d1"], index=0)
        bad = replace(
            make_chunk(document_id, tenants["c1"], tenants["d1"], index=1),
            embedding=None,
        )
        with pytest.raises(ValueError):
            store.replace_document_chunks(document_id, [good, bad])
        assert store.count_by_document_id(document_id) == 0

    def test_mixed_scope_batch_rejected_before_write(self, store, tenants):
        document_id = uuid4()
        first = make_chunk(document_id, tenants["c1"], tenants["d1"], index=0)
        second = make_chunk(document_id, tenants["c1"], tenants["d2"], index=1)
        with pytest.raises(ValueError, match="scope mismatch"):
            store.replace_document_chunks(document_id, [first, second])
        assert store.count_by_document_id(document_id) == 0

    def test_failed_replacement_preserves_prior_state(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id,
            [
                make_chunk(
                    document_id, tenants["c1"], tenants["d1"], content="ORIGINAL"
                )
            ],
        )
        broken = replace(
            make_chunk(document_id, tenants["c1"], tenants["d1"]),
            embedding_dimension=None,
        )
        with pytest.raises(ValueError):
            store.replace_document_chunks(document_id, [broken])

        # Prior state intact; nothing partial became visible.
        assert store.count_by_document_id(document_id) == 1
        assert store.list_by_document_id(document_id)[0].content == "ORIGINAL"

    def test_server_side_rejection_rolls_back_committed_slices(self, store, tenants):
        """
        A rejection from Weaviate itself must leave nothing behind.

        `insert_many` runs one request per slice, so with a small batch size the
        earlier slices commit before a later one fails. Compensation must remove
        them, since there is no transaction to roll back.
        """
        from dataclasses import replace as dc_replace

        from rag.storage.errors import StorageWriteError

        seed_doc = uuid4()
        store.replace_document_chunks(
            seed_doc,
            [make_chunk(seed_doc, tenants["c1"], tenants["d1"], seed=1)],
        )

        # Force one request per chunk so earlier ones really do commit first.
        store._config = replace(store.config, batch_size=1)

        document_id = uuid4()
        good_a = make_chunk(document_id, tenants["c1"], tenants["d1"], index=0, seed=2)
        good_b = make_chunk(document_id, tenants["c1"], tenants["d1"], index=1, seed=3)
        # Same declared dimension (so client validation passes) but a vector the
        # collection's index cannot accept.
        oversized = dc_replace(
            make_chunk(document_id, tenants["c1"], tenants["d1"], index=2, seed=4),
            embedding=unit_vector(4, dim=64),
            embedding_dimension=64,
        )

        with pytest.raises(StorageWriteError):
            store.replace_document_chunks(document_id, [good_a, good_b, oversized])

        # Compensation removed the slices that had already committed.
        assert store.count_by_document_id(document_id) == 0
        # An unrelated document is untouched.
        assert store.count_by_document_id(seed_doc) == 1

    def test_document_id_mismatch_rejected(self, store, tenants):
        document_id = uuid4()
        foreign = make_chunk(uuid4(), tenants["c1"], tenants["d1"])
        with pytest.raises(ValueError, match="document_id mismatch"):
            store.replace_document_chunks(document_id, [foreign])
        assert store.count_by_document_id(document_id) == 0


class TestScopeLimits:
    def test_oversized_document_scope_fails_closed(self, store, tenants):
        document_id = uuid4()
        store.replace_document_chunks(
            document_id, [make_chunk(document_id, tenants["c1"], tenants["d1"])]
        )
        oversized = frozenset(uuid4() for _ in range(20))
        # Shrink the cap so the authorized scope exceeds what one query can carry.
        store._config = replace(store.config, max_scope_document_ids=5)
        with pytest.raises(StorageScopeTooLargeError):
            store.search(
                unit_vector(0),
                scope_for(tenants["c1"], [tenants["d1"]], oversized),
                top_k=5,
                query_model_id=MODEL,
                query_dimension=DIM,
            )

    def test_error_types_are_backend_neutral(self):
        assert issubclass(StorageWriteError, Exception)
