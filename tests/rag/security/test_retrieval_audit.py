"""
Retrieval audit trail tests (Phase 7).

`retrieval.executed` and `authz.chunk_blocked` were required by the security
model but existed only in the specs, leaving no record of who read what. These
verify the events fire and — critically — that they never carry raw queries or
chunk content, since an audit log is long-lived.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag.audit import (
    EVENT_CHUNK_BLOCKED,
    EVENT_RETRIEVAL_EXECUTED,
    AuditLog,
    query_fingerprint,
)
from rag.authorization.context import AuthorizationContext
from rag.contracts.retrieval import RetrievedChunk
from rag.ingestion.types import DocumentStatus
from tests.rag.conftest import make_embedded_stored_chunk, make_ingest_request

SECRET_QUERY = "متن محرمانه که هرگز نباید در گزارش ممیزی ثبت شود"


def authz_for(tenant_ids, request_id, *, user="U1", departments=("C1_D1",)):
    return AuthorizationContext(
        user_id=tenant_ids["users"][user],
        company_id=tenant_ids["companies"]["C1"],
        allowed_department_ids=tuple(
            tenant_ids["departments"][name] for name in departments
        ),
        request_id=request_id,
    )


@pytest.mark.security
class TestAuditContentSafety:
    def test_raw_query_is_never_recorded(self, rag_application, tenant_ids, request_id):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="محتوای نمونه برای ممیزی"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.retrieval_service.search(
            SECRET_QUERY, request_id, tenant_ids["tokens"]["U1"]
        )
        serialized = str(
            [event.fields for event in rag_application.audit_log.events]
        )
        assert SECRET_QUERY not in serialized
        for token in SECRET_QUERY.split():
            assert token not in serialized

    def test_query_hash_is_recorded_instead(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.retrieval_service.search(
            SECRET_QUERY, request_id, tenant_ids["tokens"]["U1"]
        )
        events = rag_application.audit_log.events_named(EVENT_RETRIEVAL_EXECUTED)
        assert events
        assert events[0].fields["query_hash"] == query_fingerprint(SECRET_QUERY)

    def test_chunk_content_is_never_recorded(
        self, rag_application, tenant_ids, request_id
    ):
        marker = "نشانه محتوایی یکتا برای ممیزی"
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=marker),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.retrieval_service.search(
            marker, request_id, tenant_ids["tokens"]["U1"]
        )
        serialized = str([event.fields for event in rag_application.audit_log.events])
        assert marker not in serialized

    @pytest.mark.parametrize(
        "field", ["query", "content", "text", "embedding", "vector"]
    )
    def test_forbidden_fields_are_rejected_outright(self, field, request_id):
        log = AuditLog()
        with pytest.raises(ValueError, match="raw content"):
            log.emit("some.event", request_id, **{field: "sensitive"})

    def test_safe_fields_are_accepted(self, request_id):
        log = AuditLog()
        log.emit("some.event", request_id, query_hash="abc", chunk_ids=["x"])
        assert len(log.events) == 1


@pytest.mark.security
class TestRetrievalExecuted:
    def test_event_is_emitted_on_search(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند قابل بازیابی"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.retrieval_service.search(
            "سند قابل بازیابی", request_id, tenant_ids["tokens"]["U1"]
        )
        assert rag_application.audit_log.events_named(EVENT_RETRIEVAL_EXECUTED)

    def test_event_carries_the_identity_and_scope(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.retrieval_service.search(
            "هر پرس‌وجو", request_id, tenant_ids["tokens"]["U1"]
        )
        fields = rag_application.audit_log.events_named(EVENT_RETRIEVAL_EXECUTED)[
            0
        ].fields
        assert fields["user_id"] == str(tenant_ids["users"]["U1"])
        assert fields["company_id"] == str(tenant_ids["companies"]["C1"])
        assert fields["department_count"] == 1

    def test_event_carries_counts_and_latency(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند شمارش"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.retrieval_service.search(
            "سند شمارش", request_id, tenant_ids["tokens"]["U1"]
        )
        fields = rag_application.audit_log.events_named(EVENT_RETRIEVAL_EXECUTED)[
            0
        ].fields
        assert fields["returned_count"] >= 1
        assert fields["candidate_count"] >= fields["returned_count"]
        assert fields["latency_ms"] >= 0
        assert isinstance(fields["chunk_ids"], list)

    def test_department_count_not_department_ids(
        self, rag_application, tenant_ids, request_id
    ):
        """Cardinality only, per the security model's audit field list."""
        rag_application.retrieval_service.search(
            "پرس‌وجو", request_id, tenant_ids["tokens"]["U2"]
        )
        fields = rag_application.audit_log.events_named(EVENT_RETRIEVAL_EXECUTED)[
            0
        ].fields
        assert fields["department_count"] == 2
        assert "department_ids" not in fields

    def test_no_event_when_authorization_is_empty(
        self, rag_application, tenant_ids, request_id
    ):
        # U3 has no departments: the search short-circuits before the store.
        rag_application.retrieval_service.search(
            "پرس‌وجو", request_id, tenant_ids["tokens"]["U3"]
        )
        assert rag_application.audit_log.events_named(EVENT_RETRIEVAL_EXECUTED) == []


@pytest.mark.security
class TestChunkBlocked:
    def test_event_fires_when_the_store_returns_out_of_scope_chunks(
        self, rag_application, tenant_ids, request_id, monkeypatch
    ):
        """
        Simulate a storage regression leaking a foreign chunk.

        The engine's post-validation must strip it and record the incident.
        """
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند مجاز"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        engine = rag_application.retrieval_service._engine
        foreign = RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
            content="LEAKED CROSS TENANT CONTENT",
            score=0.99,
            chunk_index=0,
            document_version=1,
        )
        original = engine._validator.validate

        def leaky(candidates, authz):
            return original((*tuple(candidates), foreign), authz)

        monkeypatch.setattr(engine._validator, "validate", leaky)
        result = rag_application.retrieval_service.search(
            "سند مجاز", request_id, tenant_ids["tokens"]["U1"]
        )

        blocked = rag_application.audit_log.events_named(EVENT_CHUNK_BLOCKED)
        assert blocked
        assert blocked[0].fields["blocked_count"] == 1
        assert str(foreign.chunk_id) in blocked[0].fields["blocked_chunk_ids"]
        # And the leaked chunk never reaches the caller.
        assert all(
            chunk.company_id == tenant_ids["companies"]["C1"]
            for chunk in result.chunks
        )
        assert "LEAKED" not in str(result.chunks)

    def test_blocked_event_records_ids_not_content(
        self, rag_application, tenant_ids, request_id
    ):
        from rag.audit import emit_chunk_blocked

        chunk_id = uuid4()
        emit_chunk_blocked(
            rag_application.audit_log,
            request_id=request_id,
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            blocked_chunk_ids=[chunk_id],
            reason="post_validation_scope_mismatch",
        )
        fields = rag_application.audit_log.events_named(EVENT_CHUNK_BLOCKED)[0].fields
        assert fields["blocked_chunk_ids"] == [str(chunk_id)]
        assert fields["reason"] == "post_validation_scope_mismatch"
        assert "content" not in fields

    def test_no_blocked_event_on_a_clean_search(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند تمیز"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.retrieval_service.search(
            "سند تمیز", request_id, tenant_ids["tokens"]["U1"]
        )
        assert rag_application.audit_log.events_named(EVENT_CHUNK_BLOCKED) == []


@pytest.mark.security
class TestPostValidationOnRetrievePath:
    """The /retrieve endpoint now has the same L3 gate as /query."""

    def test_engine_strips_unauthorized_chunks(
        self, rag_application, tenant_ids, request_id
    ):
        engine = rag_application.retrieval_service._engine
        authz = authz_for(tenant_ids, request_id)
        foreign = RetrievedChunk(
            chunk_id=uuid4(),
            document_id=uuid4(),
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
            content="foreign",
            score=0.5,
            chunk_index=0,
            document_version=1,
        )
        authorized, blocked = engine._validator.validate([foreign], authz)
        assert authorized == ()
        assert blocked == (foreign.chunk_id,)

    def test_context_is_dropped_when_anything_was_blocked(
        self, rag_application, tenant_ids, request_id, monkeypatch
    ):
        """Context is built before validation, so it must not survive a strip."""
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند زمینه"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        engine = rag_application.retrieval_service._engine
        original = engine._validator.validate

        def strip_everything(candidates, authz):
            authorized, _ = original(candidates, authz)
            return (), tuple(chunk.chunk_id for chunk in authorized)

        monkeypatch.setattr(engine._validator, "validate", strip_everything)
        result = rag_application.retrieval_service.search(
            "سند زمینه", request_id, tenant_ids["tokens"]["U1"]
        )
        assert result.chunks == ()
        assert result.context.text == ""


@pytest.mark.security
class TestAuditLogHygiene:
    def test_buffer_is_bounded(self, request_id):
        log = AuditLog(max_events=10)
        for index in range(50):
            log.emit("test.event", request_id, index=index)
        assert len(log.events) == 10

    def test_ingestion_and_retrieval_share_one_trail(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند مشترک"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.retrieval_service.search(
            "سند مشترک", request_id, tenant_ids["tokens"]["U1"]
        )
        names = {event.name for event in rag_application.audit_log.events}
        assert "ingestion.completed" in names
        assert EVENT_RETRIEVAL_EXECUTED in names


@pytest.mark.security
class TestStatusGateIsolation:
    """The searchability gate moved into storage; it must still fail closed."""

    def test_unpublished_chunks_are_not_searchable(
        self, chunk_store, embedding_service, tenant_ids
    ):
        from rag.storage.vector_search import VectorSearchScope

        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="محتوای منتشر نشده",
            document_status=DocumentStatus.PROCESSING.value,
        )
        chunk_store.replace_document_chunks(document_id, [chunk])
        query = embedding_service.embed_query("محتوای منتشر نشده")
        results, pool = chunk_store.search(
            query.vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            ),
            top_k=10,
            query_model_id=query.model_info.model_id,
            query_dimension=query.model_info.dimension,
        )
        assert results == []
        assert pool == 0

    def test_chunks_without_a_status_fail_closed(
        self, chunk_store, embedding_service, tenant_ids
    ):
        """Legacy chunks with no status must be invisible, not visible."""
        from rag.storage.vector_search import VectorSearchScope

        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="محتوای قدیمی",
            document_status=None,
        )
        chunk_store.replace_document_chunks(document_id, [chunk])
        query = embedding_service.embed_query("محتوای قدیمی")
        results, _ = chunk_store.search(
            query.vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            ),
            top_k=10,
            query_model_id=query.model_info.model_id,
            query_dimension=query.model_info.dimension,
        )
        assert results == []

    def test_publishing_makes_chunks_searchable(
        self, chunk_store, embedding_service, tenant_ids
    ):
        from rag.storage.vector_search import VectorSearchScope

        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            content="محتوای منتشر شده",
            document_status=DocumentStatus.PROCESSING.value,
        )
        chunk_store.replace_document_chunks(document_id, [chunk])
        updated = chunk_store.set_document_status(
            document_id, DocumentStatus.INDEXED.value
        )
        assert updated == 1

        query = embedding_service.embed_query("محتوای منتشر شده")
        results, _ = chunk_store.search(
            query.vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            ),
            top_k=10,
            query_model_id=query.model_info.model_id,
            query_dimension=query.model_info.dimension,
        )
        assert len(results) == 1

    def test_status_gate_does_not_bypass_tenant_isolation(
        self, chunk_store, embedding_service, tenant_ids
    ):
        """An INDEXED chunk in another company must still be invisible."""
        from rag.storage.vector_search import VectorSearchScope

        document_id = uuid4()
        chunk = make_embedded_stored_chunk(
            embedding_service,
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
            content="محتوای شرکت دیگر",
            document_status=DocumentStatus.INDEXED.value,
        )
        chunk_store.replace_document_chunks(document_id, [chunk])
        query = embedding_service.embed_query("محتوای شرکت دیگر")
        results, _ = chunk_store.search(
            query.vector,
            VectorSearchScope(
                company_id=tenant_ids["companies"]["C1"],
                allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            ),
            top_k=10,
            query_model_id=query.model_info.model_id,
            query_dimension=query.model_info.dimension,
        )
        assert results == []

    def test_engine_no_longer_scans_all_documents(
        self, rag_application, tenant_ids, request_id
    ):
        """`list_all()` must not be called on the retrieval path."""
        calls: list[str] = []
        store = rag_application.document_store
        original = store.list_all

        def spy():
            calls.append("list_all")
            return original()

        store.list_all = spy  # type: ignore[method-assign]
        try:
            rag_application.ingestion_service.create_document(
                make_ingest_request(tenant_ids, content="سند بدون اسکن"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
            calls.clear()
            rag_application.retrieval_service.search(
                "سند بدون اسکن", request_id, tenant_ids["tokens"]["U1"]
            )
        finally:
            store.list_all = original  # type: ignore[method-assign]
        assert calls == []
