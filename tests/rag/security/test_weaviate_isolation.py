"""
Tenant-isolation security tests for the Weaviate backend (Phase 6).

These run the **whole application** — identity, authorization, retrieval, and
the Phase 4 pipeline — against a real Weaviate, because isolation is only
meaningful end to end. Skipped unless `RAG_WEAVIATE_TEST_URL` is set.

The adversarial setup is deliberate: cross-tenant documents are seeded with
*identical or near-identical embeddings* to the query, so any missing filter
surfaces as a leak rather than being masked by low similarity.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from rag.app.errors import ApiAuthenticationError, ApiAuthorizationError
from rag.app.factory import RagApplication
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.types import RetrievalApiRequest
from rag.authorization.context import AuthorizationContext
from rag.storage.vector_search import VectorSearchScope
from tests.rag.conftest import STUB_EMBEDDING_CONFIG, make_ingest_request
from tests.rag.storage_support import (
    requires_weaviate,
    unique_collection_name,
    weaviate_config,
)

pytestmark = [requires_weaviate, pytest.mark.security]

SHARED_MARKER = "سند محرمانه با نشانه مشترک برای آزمون ایزوله‌سازی"


@pytest.fixture
def weaviate_store():
    from rag.storage.weaviate.store import WeaviateChunkStore

    name = unique_collection_name("Security")
    backend = WeaviateChunkStore(weaviate_config(name))
    yield backend
    try:
        backend.client.collections.delete(name)
    finally:
        backend.close()


@pytest.fixture
def app(identity_store, ingest_permissions, weaviate_store) -> RagApplication:
    """Full application stack backed by a real Weaviate."""
    return RagApplication.build_in_memory(
        identity_store,
        ingest_permissions=ingest_permissions,
        chunk_store=weaviate_store,
        embedding_config=STUB_EMBEDDING_CONFIG,
    )


@pytest.fixture
def handler(app) -> RetrieveHandler:
    return RetrieveHandler(app.retrieval_service)


def seed_direct(app, tenant_ids, *, company, department, content):
    """
    Seed an INDEXED document straight into the stores.

    Cross-company data cannot be created through `IngestionService`: the
    authorization layer refuses a token whose company does not match, which is
    itself the correct behaviour. Seeding directly lets these tests verify the
    *retrieval* boundary against data that really exists in another tenant.
    """
    from tests.rag.conftest import make_embedded_stored_chunk

    document_id = uuid4()
    company_id = tenant_ids["companies"][company]
    department_id = tenant_ids["departments"][department]
    app.document_store.create_processing(
        company_id=company_id,
        department_id=department_id,
        source="seed",
        language="fa",
        source_type="test",
        content_hash=f"hash-{document_id}",
        normalization_version="fa-norm-v1",
        document_id=document_id,
    )
    app.document_store.mark_indexed(
        document_id, chunk_count=1, content_hash=f"hash-{document_id}"
    )
    chunk = make_embedded_stored_chunk(
        app.embedding_service,
        chunk_id=uuid4(),
        document_id=document_id,
        company_id=company_id,
        department_id=department_id,
        content=content,
    )
    app.chunk_store.replace_document_chunks(document_id, [chunk])
    return document_id


def seed(app, tenant_ids, request_id, *, company, department, content, token):
    return app.ingestion_service.create_document(
        make_ingest_request(
            tenant_ids,
            company_key=company,
            department_key=department,
            content=content,
            document_id=uuid4(),
        ),
        request_id,
        tenant_ids["tokens"][token],
    )


class TestCompanyIsolation:
    """1. Company A must not retrieve Company B."""

    def test_identical_content_is_not_visible_across_companies(
        self, app, tenant_ids, request_id, handler
    ):
        # C2 gets the document; C1's user queries for its exact text.
        seed_direct(
            app, tenant_ids, company="C2", department="C2_D1", content=SHARED_MARKER
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()
        assert response.chunk_count == 0

    def test_each_company_sees_only_its_own_copy(
        self, app, tenant_ids, request_id, handler
    ):
        own = seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content=SHARED_MARKER,
            token="U1",
        )
        seed_direct(
            app, tenant_ids, company="C2", department="C2_D1", content=SHARED_MARKER
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count >= 1
        for chunk in response.chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
            assert chunk.document_id == own.document_id

    def test_store_level_company_scope_returns_nothing(
        self, app, tenant_ids, request_id, weaviate_store
    ):
        created_id = seed_direct(
            app, tenant_ids, company="C2", department="C2_D1", content=SHARED_MARKER
        )
        vector = app.embedding_service.embed_query(SHARED_MARKER)
        # A forged scope naming C1 must not reach C2's tenant.
        results, pool = weaviate_store.search(
            vector.vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C2_D1"],),
                allowed_document_ids=frozenset({created_id}),
            ),
            top_k=10,
            query_model_id=vector.model_info.model_id,
            query_dimension=vector.model_info.dimension,
        )
        assert results == []
        assert pool == 0


class TestDepartmentIsolation:
    """2. Department A must not retrieve Department B."""

    def test_other_department_document_is_not_retrievable(
        self, app, tenant_ids, request_id, handler
    ):
        # U1 is authorized for C1_D1 only; the document lives in C1_D2.
        seed_direct(
            app, tenant_ids, company="C1", department="C1_D2", content=SHARED_MARKER
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()

    def test_multi_department_user_sees_only_authorized_departments(
        self, app, tenant_ids, request_id, handler
    ):
        # U2 is authorized for C1_D1 and C1_D3, never C1_D2.
        for department in ("C1_D1", "C1_D2", "C1_D3"):
            seed_direct(
                app,
                tenant_ids,
                company="C1",
                department=department,
                content=f"{SHARED_MARKER} {department}",
            )
        response = handler.retrieve(
            RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id, top_k=20),
            bearer_token=tenant_ids["tokens"]["U2"],
        )
        allowed = {
            tenant_ids["departments"]["C1_D1"],
            tenant_ids["departments"]["C1_D3"],
        }
        assert response.chunk_count >= 1
        for chunk in response.chunks:
            assert chunk.department_id in allowed
            assert chunk.department_id != tenant_ids["departments"]["C1_D2"]

    def test_user_with_no_departments_gets_nothing(
        self, app, tenant_ids, request_id, handler
    ):
        seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content=SHARED_MARKER,
            token="U1",
        )
        # U3 belongs to C1 but has no department grants.
        response = handler.retrieve(
            RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U3"],
        )
        assert response.chunks == ()


class TestAuthenticationGate:
    """3. An unauthorized caller must not be able to trigger a vector search."""

    def test_unauthenticated_request_rejected(self, handler, request_id):
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id),
                bearer_token=None,
            )

    def test_invalid_token_rejected(self, handler, tenant_ids, request_id):
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id),
                bearer_token=tenant_ids["tokens"]["INVALID"],
            )

    def test_revoked_token_rejected(self, handler, tenant_ids, request_id):
        with pytest.raises((ApiAuthenticationError, ApiAuthorizationError)):
            handler.retrieve(
                RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id),
                bearer_token=tenant_ids["tokens"]["REVOKED"],
            )

    def test_empty_scope_never_reaches_the_vector_store(
        self, app, tenant_ids, request_id
    ):
        """A user with no departments must short-circuit before any query."""
        calls: list[str] = []
        original = app.chunk_store.search

        def spy(*args, **kwargs):
            calls.append("search")
            return original(*args, **kwargs)

        app.chunk_store.search = spy  # type: ignore[method-assign]
        try:
            authz = AuthorizationContext(
                user_id=tenant_ids["users"]["U3"],
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(),
                request_id=request_id,
            )
            result = app.retrieval_service._engine.search(SHARED_MARKER, authz)
        finally:
            app.chunk_store.search = original  # type: ignore[method-assign]
        assert result.chunks == ()
        assert calls == []


class TestFilterInjection:
    """4. The caller must not be able to supply tenant or scope parameters."""

    @pytest.mark.parametrize(
        "field",
        [
            "company_id",
            "department_id",
            "department_ids",
            "allowed_department_ids",
            "document_ids",
            "filters",
            "filter_override",
            "skip_authz",
        ],
    )
    def test_scope_fields_rejected_at_the_api(self, handler, request_id, field):
        from rag.app.errors import ApiValidationError

        body = {
            "query": SHARED_MARKER,
            "request_id": str(request_id),
            field: "attacker-supplied",
        }
        with pytest.raises(ApiValidationError):
            handler.parse_request(body)

    def test_tenant_and_collection_are_not_request_parameters(self, handler, request_id):
        from rag.app.errors import ApiValidationError

        for field in ("tenant", "collection", "class"):
            body = {
                "query": SHARED_MARKER,
                "request_id": str(request_id),
                field: "OtherTenant",
            }
            # Unknown fields are ignored, never forwarded to the store.
            try:
                parsed = handler.parse_request(body)
            except ApiValidationError:
                continue
            assert not hasattr(parsed, field)

    def test_engine_rejects_caller_supplied_filter_kwargs(
        self, app, tenant_ids, request_id
    ):
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        with pytest.raises(TypeError):
            app.retrieval_service._engine.search(
                SHARED_MARKER, authz, None, company_id=tenant_ids["companies"]["C2"]
            )

    def test_adapter_rejects_out_of_scope_objects(self, weaviate_store, tenant_ids):
        """Defence in depth: an out-of-scope object must be refused, not returned."""
        from rag.ingestion.types import StoredChunk
        from rag.storage.errors import StorageWriteError

        foreign = StoredChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
            document_version=1,
            chunk_index=0,
            content="foreign",
            content_hash="h",
        )
        scope = VectorSearchScope(
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            allowed_document_ids=frozenset({uuid4()}),
        )
        with pytest.raises(StorageWriteError):
            weaviate_store._assert_object_scope(foreign, scope)


class TestFailedIngestion:
    """5. A failed ingestion must not leave partial vectors searchable."""

    def test_failed_persistence_leaves_nothing_retrievable(
        self, app, tenant_ids, request_id, handler, weaviate_store
    ):
        from rag.ingestion.errors import IngestPipelineError

        marker = "متن ناموفق برای آزمون شکست نگهداری"
        original = weaviate_store.replace_document_chunks

        def failing(document_id, chunks):
            # Write nothing, then fail — as a rejected batch would.
            raise RuntimeError("simulated vector store failure")

        weaviate_store.replace_document_chunks = failing  # type: ignore[method-assign]
        try:
            with pytest.raises(IngestPipelineError):
                seed(
                    app,
                    tenant_ids,
                    request_id,
                    company="C1",
                    department="C1_D1",
                    content=marker,
                    token="U1",
                )
        finally:
            weaviate_store.replace_document_chunks = original  # type: ignore[method-assign]

        response = handler.retrieve(
            RetrievalApiRequest(query=marker, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()

    def test_partially_written_chunks_are_not_searchable(
        self, app, tenant_ids, request_id, handler, weaviate_store
    ):
        """
        Even if objects reach Weaviate, the document never becomes INDEXED, so
        the status gate keeps them unreachable.
        """
        from rag.ingestion.errors import IngestPipelineError

        marker = "متن نیمه‌نوشته برای آزمون اتمی بودن"
        original = weaviate_store.replace_document_chunks

        def partial(document_id, chunks):
            original(document_id, list(chunks)[:1])
            raise RuntimeError("failed after writing one chunk")

        weaviate_store.replace_document_chunks = partial  # type: ignore[method-assign]
        try:
            with pytest.raises(IngestPipelineError):
                seed(
                    app,
                    tenant_ids,
                    request_id,
                    company="C1",
                    department="C1_D1",
                    content=marker,
                    token="U1",
                )
        finally:
            weaviate_store.replace_document_chunks = original  # type: ignore[method-assign]

        response = handler.retrieve(
            RetrievalApiRequest(query=marker, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()


class TestDeletionAndUpdate:
    """6 & 7. Deleted documents unreachable; updates return no stale chunks."""

    def test_deleted_document_is_not_retrievable(
        self, app, tenant_ids, request_id, handler
    ):
        marker = "سند حذف‌شده با نشانه یکتا"
        created = seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content=marker,
            token="U1",
        )
        before = handler.retrieve(
            RetrievalApiRequest(query=marker, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert before.chunk_count >= 1

        app.ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["U1"]
        )
        after = handler.retrieve(
            RetrievalApiRequest(query=marker, request_id=request_id, top_k=10),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert after.chunks == ()

    def test_updated_document_returns_no_stale_content(
        self, app, tenant_ids, request_id, handler
    ):
        from rag.ingestion.types import IngestDocumentUpdateRequest

        created = seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content="محتوای کهنه با نشانه قدیمی",
            token="U1",
        )
        app.ingestion_service.update_document(
            created.document_id,
            IngestDocumentUpdateRequest(
                content="محتوای تازه با نشانه جدید",
                company_id=tenant_ids["companies"]["C1"],
                department_id=tenant_ids["departments"]["C1_D1"],
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        response = handler.retrieve(
            RetrievalApiRequest(
                query="نشانه قدیمی", request_id=request_id, top_k=10
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        for chunk in response.chunks:
            assert "کهنه" not in chunk.content
            assert "قدیمی" not in chunk.content


class TestNoVectorExposure:
    """8. Raw vectors must never leave the public API."""

    def test_api_response_contains_no_vector(
        self, app, tenant_ids, request_id, handler
    ):
        seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content=SHARED_MARKER,
            token="U1",
        )
        response = handler.retrieve(
            RetrievalApiRequest(query=SHARED_MARKER, request_id=request_id, top_k=5),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        payload = response.to_dict()
        serialized = str(payload)
        for banned in ("embedding", "vector", "float32"):
            assert banned not in serialized.lower()

    def test_search_results_carry_no_embedding(
        self, app, tenant_ids, request_id, weaviate_store
    ):
        created = seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content=SHARED_MARKER,
            token="U1",
        )
        query = app.embedding_service.embed_query(SHARED_MARKER)
        results, _ = weaviate_store.search(
            query.vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
                allowed_document_ids=frozenset({created.document_id}),
            ),
            top_k=5,
            query_model_id=query.model_info.model_id,
            query_dimension=query.model_info.dimension,
        )
        assert results
        for item in results:
            assert item.chunk.embedding is None

    def test_http_response_body_has_no_vectors(
        self, app, tenant_ids, request_id, handler
    ):
        from rag.app.router import RagHttpApplication

        seed(
            app,
            tenant_ids,
            request_id,
            company="C1",
            department="C1_D1",
            content=SHARED_MARKER,
            token="U1",
        )
        status, body = RagHttpApplication(handler).dispatch(
            "POST",
            "/api/v1/rag/retrieve",
            {
                "query": SHARED_MARKER,
                "request_id": str(request_id),
                "top_k": 3,
            },
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 200
        assert "embedding" not in str(body)


class TestScopeIntegrity:
    def test_scope_is_derived_from_authorization_not_the_request(
        self, app, tenant_ids, request_id
    ):
        """The adapter receives exactly the authorized scope, nothing more."""
        captured: list[VectorSearchScope] = []
        original = app.chunk_store.search

        def spy(query_vector, scope, **kwargs):
            captured.append(scope)
            return original(query_vector, scope, **kwargs)

        app.chunk_store.search = spy  # type: ignore[method-assign]
        try:
            seed(
                app,
                tenant_ids,
                request_id,
                company="C1",
                department="C1_D1",
                content=SHARED_MARKER,
                token="U1",
            )
            RetrieveHandler(app.retrieval_service).retrieve(
                RetrievalApiRequest(
                    query=SHARED_MARKER, request_id=request_id, top_k=5
                ),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
        finally:
            app.chunk_store.search = original  # type: ignore[method-assign]

        assert captured
        scope = captured[0]
        assert scope.company_id == tenant_ids["companies"]["C1"]
        assert scope.allowed_department_ids == (tenant_ids["departments"]["C1_D1"],)

    def test_scope_dataclass_is_immutable(self, tenant_ids):
        scope = VectorSearchScope(
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            allowed_document_ids=frozenset(),
        )
        with pytest.raises((AttributeError, TypeError)):
            scope.company_id = tenant_ids["companies"]["C2"]  # type: ignore[misc]
        # Producing a widened copy is possible, but the adapter never does it.
        widened = replace(scope, company_id=tenant_ids["companies"]["C2"])
        assert widened.company_id != scope.company_id
