"""
Production embedding model: BAAI/bge-m3.

Marked `bench` because it loads a ~2 GB model; the default suite stays fast and
dependency-free. Run with:

    python -m pytest -m bench tests/integration/embedding/test_production_model.py

Config-level assertions are NOT marked, so the default suite still catches an
accidental change to the production selection.
"""

from __future__ import annotations

import time
from uuid import uuid4

import numpy as np
import pytest
from tests.rag.storage_support import requires_weaviate

from rag.embedding.config import load_embedding_config
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel

PRODUCTION_MODEL_ID = "BAAI/bge-m3"
PRODUCTION_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
PRODUCTION_DIMENSION = 1024

PERSIAN_QUERY = "مرخصی سالانه کارکنان تمام‌وقت چند روز است؟"
PERSIAN_DOCS = [
    "سیاست مرخصی سالانه برای کارکنان تمام‌وقت ۲۶ روز است.",
    "راهنمای فنی سرور: پورت ۸۰۸۰ برای بررسی سلامت استفاده می‌شود.",
    "برای اتصال VPN از احراز هویت دو مرحله‌ای استفاده کنید.",
]


# ---------------------------------------------------------------- config only


class TestProductionSelection:
    """Fast assertions — these run in the default suite."""

    def test_production_model_is_selected(self):
        config = load_embedding_config()
        assert config.model_id == PRODUCTION_MODEL_ID
        assert config.production is True
        assert config.backend == "sentence-transformers"

    def test_revision_is_pinned(self):
        """An unpinned revision would let upstream silently change embeddings."""
        config = load_embedding_config()
        assert config.revision == PRODUCTION_REVISION

    def test_stub_is_no_longer_the_production_backend(self):
        config = load_embedding_config()
        assert config.backend != "stub"
        assert config.model_id != "stub-v1"

    def test_stub_remains_available_for_tests(self):
        """Removing stub-v1 from production must not remove it from the codebase."""
        stub = StubEmbeddingModel(dimension=384, model_id="stub-v1")
        assert stub.health_check() is True
        assert stub.info.dimension == 384

    def test_no_prefixes_required(self):
        """
        bge-m3 is symmetric. e5 needs "query: "/"passage: ", which is one more
        way for the query and document paths to drift apart.
        """
        config = load_embedding_config()
        assert config.query_prefix is None
        assert config.document_prefix is None

    def test_embeddings_are_normalised(self):
        # Cosine == dot product only if vectors are unit length.
        assert load_embedding_config().normalize_embeddings is True

    def test_registry_supports_the_production_backend(self):
        assert "sentence-transformers" in ModelRegistry.list_registered_backends()

    def test_model_libraries_are_not_imported_eagerly(self):
        """Importing the registry must not drag in torch at process start."""
        import subprocess
        import sys
        from pathlib import Path

        root = str(Path(__file__).resolve().parents[4])
        code = (
            f"import sys; sys.path.insert(0, r'{root}');"
            "import rag.embedding.registry;"
            "print('torch' in sys.modules, 'sentence_transformers' in sys.modules)"
        )
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        assert out.stdout.strip() == "False False"


# ------------------------------------------------------------ real model load


@pytest.fixture(scope="module")
def service():
    config = load_embedding_config()
    model = ModelRegistry.create(config)
    return EmbeddingService(
        model, EmbeddingPreprocessor(config.preprocessing.normalization_version)
    )


@pytest.fixture(scope="module")
def application(tenant_ids):
    from tests.rag.conftest import build_identity_store_for

    from rag.app.factory import RagApplication
    from rag.ingestion.authz import IngestPermissionRegistry

    permissions = IngestPermissionRegistry()
    permissions.grant_company_wide(tenant_ids["users"]["S1"])
    return RagApplication.build_in_memory(
        build_identity_store_for(tenant_ids),
        ingest_permissions=permissions,
        embedding_config=load_embedding_config(),
    )


def ingest(application, tenant_ids, content: str):
    """Ingest with a unique marker so content-hash dedup never fires."""
    from tests.rag.conftest import make_ingest_request

    return application.ingestion_service.create_document(
        make_ingest_request(
            tenant_ids, content=f"{content} [{uuid4().hex[:8]}]", document_id=uuid4()
        ),
        uuid4(),
        tenant_ids["tokens"]["U1"],
    )


@pytest.mark.bench
class TestProductionModelLoads:
    def test_model_loads(self, service):
        assert service.health_check() is True
        assert service.model_info.model_id == PRODUCTION_MODEL_ID

    def test_measured_dimension_matches_expectation(self, service):
        # Measured from the loaded model, never trusted from config.
        assert service.model_info.dimension == PRODUCTION_DIMENSION

    def test_query_and_document_dimensions_are_identical(self, service):
        query = service.embed_query(PERSIAN_QUERY)
        docs = service.embed_documents(PERSIAN_DOCS)
        assert query.vector.shape[0] == PRODUCTION_DIMENSION
        assert all(v.shape[0] == PRODUCTION_DIMENSION for v in docs.vectors)
        assert query.vector.shape[0] == docs.vectors[0].shape[0]

    def test_vectors_are_float32(self, service):
        """The chunk store rejects anything else."""
        assert service.embed_query(PERSIAN_QUERY).vector.dtype == np.float32
        assert service.embed_documents(PERSIAN_DOCS).vectors[0].dtype == np.float32

    def test_vectors_are_unit_length(self, service):
        vector = service.embed_query(PERSIAN_QUERY).vector
        assert float(np.linalg.norm(vector)) == pytest.approx(1.0, abs=1e-4)

    def test_embedding_is_deterministic(self, service):
        first = service.embed_query(PERSIAN_QUERY).vector
        second = service.embed_query(PERSIAN_QUERY).vector
        assert np.allclose(first, second, atol=1e-6)

    def test_persian_semantics_rank_the_right_document(self, service):
        """The whole point of selecting a real model."""
        query = service.embed_query(PERSIAN_QUERY).vector
        docs = service.embed_documents(PERSIAN_DOCS).vectors
        scores = [float(np.dot(query, d)) for d in docs]
        assert scores[0] == max(scores), scores

    def test_arabic_variant_query_still_matches(self, service):
        """ي/ك normalization happens before embedding, so both spellings agree."""
        persian = service.embed_query("مرخصی سالانه").vector
        arabic = service.embed_query("مرخصي سالانه").vector
        assert float(np.dot(persian, arabic)) > 0.99

    def test_zwnj_variants_agree(self, service):
        joined = service.embed_query("تمام‌وقت").vector
        spaced = service.embed_query("تمام وقت").vector
        assert float(np.dot(joined, spaced)) > 0.95

    def test_query_document_symmetry_through_the_preprocessor(self, service):
        """Same text embedded as query and as document must agree."""
        text = "سیاست مرخصی سالانه"
        as_query = service.embed_query(text).vector
        as_document = service.embed_documents([text]).vectors[0]
        assert float(np.dot(as_query, as_document)) == pytest.approx(1.0, abs=1e-3)


@pytest.mark.bench
class TestProductionModelEndToEnd:
    """ingest → embed → store → retrieve with the real model."""

    def test_dimension_recorded_on_stored_chunks(self, application, tenant_ids):
        response = ingest(application, tenant_ids, PERSIAN_DOCS[0])
        chunks = application.chunk_store.list_by_document_id(response.document_id)
        assert chunks
        for chunk in chunks:
            assert chunk.embedding_dimension == PRODUCTION_DIMENSION
            assert chunk.embedding_model_id == PRODUCTION_MODEL_ID
            assert chunk.embedding.dtype == np.float32

    def test_ingest_then_retrieve(self, application, tenant_ids):
        from rag.app.handlers.retrieve import RetrieveHandler
        from rag.app.types import RetrievalApiRequest

        for content in PERSIAN_DOCS:
            ingest(application, tenant_ids, content)
        handler = RetrieveHandler(
            application.retrieval_service,
            application.rate_limiter,
            application.request_limits,
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=PERSIAN_QUERY, request_id=uuid4(), top_k=3),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count >= 1
        # The leave-policy document must win over the VPN and server docs.
        assert "مرخصی" in response.chunks[0].content

    def test_no_raw_vector_in_the_response(self, application, tenant_ids):
        from rag.app.handlers.retrieve import RetrieveHandler
        from rag.app.types import RetrievalApiRequest

        ingest(application, tenant_ids, PERSIAN_DOCS[0])
        handler = RetrieveHandler(
            application.retrieval_service,
            application.rate_limiter,
            application.request_limits,
        )
        payload = str(
            handler.retrieve(
                RetrievalApiRequest(query=PERSIAN_QUERY, request_id=uuid4(), top_k=3),
                bearer_token=tenant_ids["tokens"]["U1"],
            ).to_dict()
        )
        assert "embedding" not in payload.lower()


@pytest.mark.bench
class TestProductionModelPerformance:
    def test_load_and_latency_within_budget(self):
        """CPU soft targets from benchmark-spec §3.3: query p95 < 200 ms."""
        config = load_embedding_config()
        started = time.perf_counter()
        model = ModelRegistry.create(config)
        load_seconds = time.perf_counter() - started
        service = EmbeddingService(
            model, EmbeddingPreprocessor(config.preprocessing.normalization_version)
        )

        service.embed_query(PERSIAN_QUERY)  # warm up
        latencies = []
        for _ in range(20):
            started = time.perf_counter()
            service.embed_query(PERSIAN_QUERY)
            latencies.append((time.perf_counter() - started) * 1000)
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95) - 1]

        print(f"\n  load={load_seconds:.1f}s p50={latencies[len(latencies)//2]:.1f}ms p95={p95:.1f}ms")

        # Deliberately a loose sanity bound, not the budget check. Measured
        # p95 varies ~3x with machine load (167 ms isolated vs 471 ms during
        # a full suite run), so a tight threshold would be flaky rather than
        # informative. The authoritative latency figure is the isolated
        # benchmark recorded in reports/selection-decision.md; this test
        # exists to catch a model that is fundamentally broken or hanging.
        assert p95 < 5000, f"query p95 {p95:.1f} ms indicates a broken model"


@pytest.mark.bench
@requires_weaviate
class TestProductionModelWithWeaviate:
    """
    The combination that actually ships: bge-m3 (1024-d) into real Weaviate.

    Requires both the model and a live instance, so it carries both gates.
    """

    @pytest.fixture
    def weaviate_application(self, tenant_ids):
        from tests.rag.conftest import build_identity_store_for
        from tests.rag.storage_support import unique_collection_name, weaviate_config

        from rag.app.factory import RagApplication
        from rag.ingestion.authz import IngestPermissionRegistry
        from rag.storage.weaviate.store import WeaviateChunkStore

        name = unique_collection_name("ProdModel")
        store = WeaviateChunkStore(weaviate_config(name))
        permissions = IngestPermissionRegistry()
        permissions.grant_company_wide(tenant_ids["users"]["S1"])
        app = RagApplication.build_in_memory(
            build_identity_store_for(tenant_ids),
            ingest_permissions=permissions,
            chunk_store=store,
            embedding_config=load_embedding_config(),
        )
        yield app
        try:
            store.client.collections.delete(name)
        finally:
            store.close()

    def test_weaviate_accepts_1024_dimensional_vectors(
        self, weaviate_application, tenant_ids
    ):
        response = ingest(weaviate_application, tenant_ids, PERSIAN_DOCS[0])
        stored = weaviate_application.chunk_store.list_by_document_id(
            response.document_id
        )
        assert stored
        assert all(c.embedding_dimension == PRODUCTION_DIMENSION for c in stored)
        assert all(c.embedding.shape[0] == PRODUCTION_DIMENSION for c in stored)

    def test_ingest_embed_store_retrieve_end_to_end(
        self, weaviate_application, tenant_ids
    ):
        from rag.app.handlers.retrieve import RetrieveHandler
        from rag.app.types import RetrievalApiRequest

        for content in PERSIAN_DOCS:
            ingest(weaviate_application, tenant_ids, content)

        handler = RetrieveHandler(
            weaviate_application.retrieval_service,
            weaviate_application.rate_limiter,
            weaviate_application.request_limits,
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=PERSIAN_QUERY, request_id=uuid4(), top_k=3),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count >= 1
        # Real semantics through the real store: leave policy beats VPN/server.
        assert "مرخصی" in response.chunks[0].content

    def test_company_isolation_holds_with_the_production_model(
        self, weaviate_application, tenant_ids
    ):
        """Identical content in another company must stay invisible."""
        from tests.rag.conftest import make_embedded_stored_chunk

        from rag.app.handlers.retrieve import RetrieveHandler
        from rag.app.types import RetrievalApiRequest

        ingest(weaviate_application, tenant_ids, PERSIAN_DOCS[0])

        foreign_doc = uuid4()
        weaviate_application.document_store.create_processing(
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
            source="seed",
            language="fa",
            source_type="test",
            content_hash=f"h-{foreign_doc}",
            normalization_version="fa-norm-v1",
            document_id=foreign_doc,
        )
        weaviate_application.document_store.mark_indexed(
            foreign_doc, chunk_count=1, content_hash=f"h-{foreign_doc}"
        )
        chunk = make_embedded_stored_chunk(
            weaviate_application.embedding_service,
            chunk_id=uuid4(),
            document_id=foreign_doc,
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
            content=PERSIAN_DOCS[0] + " SECRET-C2",
        )
        weaviate_application.chunk_store.replace_document_chunks(foreign_doc, [chunk])

        handler = RetrieveHandler(
            weaviate_application.retrieval_service,
            weaviate_application.rate_limiter,
            weaviate_application.request_limits,
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=PERSIAN_QUERY, request_id=uuid4(), top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert all(
            c.company_id == tenant_ids["companies"]["C1"] for c in response.chunks
        )
        assert "SECRET-C2" not in str(response.to_dict())

    def test_department_isolation_holds_with_the_production_model(
        self, weaviate_application, tenant_ids
    ):
        from tests.rag.conftest import make_embedded_stored_chunk

        from rag.app.handlers.retrieve import RetrieveHandler
        from rag.app.types import RetrievalApiRequest

        other_doc = uuid4()
        weaviate_application.document_store.create_processing(
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D2"],
            source="seed",
            language="fa",
            source_type="test",
            content_hash=f"h-{other_doc}",
            normalization_version="fa-norm-v1",
            document_id=other_doc,
        )
        weaviate_application.document_store.mark_indexed(
            other_doc, chunk_count=1, content_hash=f"h-{other_doc}"
        )
        chunk = make_embedded_stored_chunk(
            weaviate_application.embedding_service,
            chunk_id=uuid4(),
            document_id=other_doc,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D2"],
            content=PERSIAN_DOCS[0] + " OTHER-DEPT",
        )
        weaviate_application.chunk_store.replace_document_chunks(other_doc, [chunk])

        handler = RetrieveHandler(
            weaviate_application.retrieval_service,
            weaviate_application.rate_limiter,
            weaviate_application.request_limits,
        )
        # U1 is authorized for C1_D1 only.
        response = handler.retrieve(
            RetrievalApiRequest(query=PERSIAN_QUERY, request_id=uuid4(), top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert "OTHER-DEPT" not in str(response.to_dict())

    def test_retrieval_latency_with_weaviate(self, weaviate_application, tenant_ids):
        import time as _time

        from rag.app.handlers.retrieve import RetrieveHandler
        from rag.app.types import RetrievalApiRequest

        for content in PERSIAN_DOCS:
            ingest(weaviate_application, tenant_ids, content)
        handler = RetrieveHandler(
            weaviate_application.retrieval_service,
            weaviate_application.rate_limiter,
            weaviate_application.request_limits,
        )
        latencies = []
        for _ in range(10):
            started = _time.perf_counter()
            handler.retrieve(
                RetrievalApiRequest(query=PERSIAN_QUERY, request_id=uuid4(), top_k=5),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
            latencies.append((_time.perf_counter() - started) * 1000)
        latencies.sort()
        median = latencies[len(latencies) // 2]
        print(f"\n  weaviate retrieval (embed+search): p50={median:.1f}ms p95={latencies[-1]:.1f}ms")
        assert median < 2000
