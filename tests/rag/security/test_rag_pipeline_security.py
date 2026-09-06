"""
Security regression tests for the post-retrieval RAG pipeline.

PP-SEC-020..023 (authorization carry-through), PP-SEC-030..033 (data vs
instructions), PP-SEC-050..052 (edge cases), plus cross-company and
cross-department isolation asserted *after* reranking and context assembly.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from rag.app.errors import ApiAuthenticationError, ApiValidationError
from rag.app.handlers.query import RagQueryApiRequest, RagQueryHandler
from rag.authorization.context import AuthorizationContext
from rag.pipeline.context_builder import assemble_text, citation_id, render_source_block
from rag.pipeline.errors import UnauthorizedChunkInPipelineError
from rag.pipeline.pipeline import PostRetrievalPipeline
from rag.pipeline.serialization import rag_result_to_dict
from rag.pipeline.tokenizer import CharEstimateTokenCounter
from rag.pipeline.types import AppliedFilter, PipelineOptions, RetrievalMetadata
from rag.pipeline.validation import CandidateAuthorizationValidator
from tests.rag.conftest import (
    make_embedded_stored_chunk,
    make_ingest_request,
    make_retrieved_chunk,
)


def _authz(tenant_ids, request_id, *, user="U1", company="C1", departments=("C1_D1",)):
    return AuthorizationContext(
        user_id=tenant_ids["users"][user],
        company_id=tenant_ids["companies"][company],
        allowed_department_ids=tuple(
            tenant_ids["departments"][key] for key in departments
        ),
        request_id=request_id,
    )


def _metadata(tenant_ids, count: int, departments: int = 1) -> RetrievalMetadata:
    return RetrievalMetadata(
        chunk_count=count,
        latency_ms=1,
        filter_applied=AppliedFilter(
            company_id=tenant_ids["companies"]["C1"],
            department_count=departments,
        ),
    )


def _seed_foreign_company_document(rag_application, tenant_ids, content: str):
    """Index a C2 document directly in the shared stores."""
    document_id = uuid4()
    company = tenant_ids["companies"]["C2"]
    department = tenant_ids["departments"]["C2_D1"]
    rag_application.document_store.create_processing(
        company_id=company,
        department_id=department,
        source="seed",
        language="fa",
        source_type="test",
        content_hash="c2-hash",
        normalization_version="fa-norm-v1",
        document_id=document_id,
    )
    rag_application.document_store.mark_indexed(
        document_id, chunk_count=1, content_hash="c2-hash"
    )
    chunk = make_embedded_stored_chunk(
        rag_application.embedding_service,
        chunk_id=uuid4(),
        document_id=document_id,
        company_id=company,
        department_id=department,
        content=content,
    )
    rag_application.chunk_store.replace_document_chunks(document_id, [chunk])
    return document_id


@pytest.mark.security
class TestAuthorizationCarryThrough:
    def test_pp_sec_021_unauthorized_chunk_is_stripped_before_rerank(
        self, tenant_ids, request_id
    ):
        authorized = make_retrieved_chunk(
            "authorized body",
            score=0.5,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        foreign_company = make_retrieved_chunk(
            "other company secret",
            score=0.99,
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
        )
        foreign_department = make_retrieved_chunk(
            "other department secret",
            score=0.98,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D2"],
        )
        result = PostRetrievalPipeline().process(
            "secret",
            _authz(tenant_ids, request_id),
            [foreign_company, foreign_department, authorized],
            _metadata(tenant_ids, 3),
            PipelineOptions(rerank=True, top_k=10),
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].chunk_id == authorized.chunk_id
        assert "other company secret" not in result.context.text
        assert "other department secret" not in result.context.text
        assert result.pipeline.blocked_chunk_count == 2

    def test_pp_sec_021_strict_mode_fails_closed(self, tenant_ids, request_id):
        foreign = make_retrieved_chunk(
            "other company secret",
            score=0.99,
            company_id=tenant_ids["companies"]["C2"],
            department_id=tenant_ids["departments"]["C2_D1"],
        )
        validator = CandidateAuthorizationValidator(strict=True)
        with pytest.raises(UnauthorizedChunkInPipelineError):
            validator.validate([foreign], _authz(tenant_ids, request_id))

    def test_pp_sec_022_output_chunks_match_authorized_scope(
        self, tenant_ids, request_id
    ):
        authz = _authz(tenant_ids, request_id, user="U2", departments=("C1_D1", "C1_D3"))
        candidates = [
            make_retrieved_chunk(
                f"body {index}",
                score=0.9 - index * 0.01,
                company_id=tenant_ids["companies"]["C1"],
                department_id=tenant_ids["departments"][key],
            )
            for index, key in enumerate(("C1_D1", "C1_D3", "C1_D2"))
        ]
        result = PostRetrievalPipeline().process(
            "body", authz, candidates, _metadata(tenant_ids, 3, 2), PipelineOptions()
        )
        allowed = set(authz.allowed_department_ids)
        for chunk in result.chunks:
            assert chunk.company_id == authz.company_id
            assert chunk.department_id in allowed

    def test_pp_sec_023_source_departments_within_allowed_set(
        self, tenant_ids, request_id
    ):
        authz = _authz(tenant_ids, request_id)
        candidates = [
            make_retrieved_chunk(
                "body",
                score=0.9,
                company_id=tenant_ids["companies"]["C1"],
                department_id=tenant_ids["departments"]["C1_D1"],
            )
        ]
        result = PostRetrievalPipeline().process(
            "body", authz, candidates, _metadata(tenant_ids, 1), PipelineOptions()
        )
        for source in result.sources:
            assert source.department_id in set(authz.allowed_department_ids)

    def test_pipeline_requires_authorization_context(self, tenant_ids):
        from rag.authorization.errors import MissingAuthorizationContextError

        with pytest.raises(MissingAuthorizationContextError):
            PostRetrievalPipeline().process(
                "query", None, [], _metadata(tenant_ids, 0), PipelineOptions()
            )

    def test_empty_department_scope_yields_no_context(self, tenant_ids, request_id):
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U3"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(),
            request_id=request_id,
        )
        candidate = make_retrieved_chunk(
            "body",
            score=0.9,
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        result = PostRetrievalPipeline().process(
            "body", authz, [candidate], _metadata(tenant_ids, 1, 0), PipelineOptions()
        )
        assert result.chunks == ()
        assert result.context.text == ""


@pytest.mark.security
class TestEndToEndTenantIsolation:
    def test_cross_company_isolation_after_rerank_and_context(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند محرمانه شرکت یک"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        _seed_foreign_company_document(
            rag_application, tenant_ids, "سند محرمانه شرکت دو"
        )

        result = rag_application.rag_orchestrator.execute(
            "سند محرمانه",
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert result.chunks
        for chunk in result.chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
        assert "شرکت دو" not in result.context.text
        assert result.identity.company_id == tenant_ids["companies"]["C1"]

    def test_cross_company_isolation_with_rerank_enabled(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="گزارش مالی شرکت یک"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        _seed_foreign_company_document(
            rag_application, tenant_ids, "گزارش مالی شرکت دو"
        )
        options = rag_application.pipeline_config.to_options(rerank=True, top_k=10)
        result = rag_application.rag_orchestrator.execute(
            "گزارش مالی",
            request_id,
            tenant_ids["tokens"]["U1"],
            options=options,
        )
        for chunk in result.chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
        assert "شرکت دو" not in result.context.text

    def test_cross_department_isolation_after_context_assembly(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="راز بخش دو",
                department_key="C1_D2",
            ),
            request_id,
            tenant_ids["tokens"]["S1"],
        )
        result = rag_application.rag_orchestrator.execute(
            "راز بخش دو",
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert result.chunks == ()
        assert result.context.text == ""
        assert result.context.block_count == 0

    def test_sources_never_reference_unauthorized_documents(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند مجاز بخش یک"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        foreign_document_id = _seed_foreign_company_document(
            rag_application, tenant_ids, "سند غیرمجاز"
        )
        result = rag_application.rag_orchestrator.execute(
            "سند",
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        referenced = {source.document_id for source in result.sources}
        assert foreign_document_id not in referenced
        for record in result.provenance:
            assert record.document_id != foreign_document_id

    def test_deleted_document_never_enters_context(
        self, rag_application, tenant_ids, request_id
    ):
        created = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند حذف شده pipeline"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        rag_application.ingestion_service.delete_document(
            created.document_id, request_id, tenant_ids["tokens"]["U1"]
        )
        result = rag_application.rag_orchestrator.execute(
            "سند حذف شده pipeline",
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert result.chunks == ()
        assert result.context.text == ""


@pytest.mark.security
class TestApiBoundary:
    def test_unauthenticated_query_rejected(self, rag_query_handler, request_id):
        with pytest.raises(ApiAuthenticationError):
            rag_query_handler.query(
                RagQueryApiRequest(query="secret", request_id=request_id),
                bearer_token=None,
            )

    def test_invalid_token_rejected(self, rag_query_handler, tenant_ids, request_id):
        with pytest.raises(ApiAuthenticationError):
            rag_query_handler.query(
                RagQueryApiRequest(query="secret", request_id=request_id),
                bearer_token=tenant_ids["tokens"]["INVALID"],
            )

    @pytest.mark.parametrize(
        "forbidden_key",
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
    def test_caller_supplied_scope_rejected(self, request_id, forbidden_key):
        body = {
            "query": "secret",
            "request_id": str(request_id),
            forbidden_key: "anything",
        }
        with pytest.raises(ApiValidationError):
            RagQueryHandler.parse_request(body)

    def test_router_rejects_forged_scope(self, rag_http_app, tenant_ids, request_id):
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/query",
            {
                "query": "secret",
                "request_id": str(request_id),
                "company_id": str(tenant_ids["companies"]["C2"]),
            },
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 400
        assert body["code"] == "API_VALIDATION_ERROR"

    def test_pp_sec_030_response_has_no_instruction_channel(
        self, rag_application, rag_http_app, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند عمومی برای پاسخ"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/query",
            {"query": "سند عمومی", "request_id": str(request_id), "top_k": 5},
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 200
        for prohibited in ("answer", "system_prompt", "system_instructions", "messages"):
            assert prohibited not in body

    def test_no_raw_vectors_in_http_response(
        self, rag_application, rag_http_app, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند برداری"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        _status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/query",
            {"query": "سند برداری", "request_id": str(request_id)},
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        serialized = json.dumps(body, ensure_ascii=False).lower()
        for banned in ("embedding", "vector"):
            assert banned not in serialized

    def test_pp_sec_054_raw_query_not_echoed(
        self, rag_application, rag_http_app, tenant_ids, request_id
    ):
        secret_query = "کلمه بسیار محرمانه جستجو"
        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="محتوای عادی"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        _status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/query",
            {"query": secret_query, "request_id": str(request_id)},
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert secret_query not in json.dumps(body, ensure_ascii=False)
        assert len(body["query_hash"]) == 64


@pytest.mark.security
class TestEdgeCases:
    def test_pp_sec_050_zero_candidates(self, tenant_ids, request_id):
        result = PostRetrievalPipeline().process(
            "query",
            _authz(tenant_ids, request_id),
            [],
            _metadata(tenant_ids, 0),
            PipelineOptions(),
        )
        assert result.chunks == ()
        assert result.sources == ()
        assert result.provenance == ()
        assert result.context.text == ""
        assert result.context.block_count == 0
        assert result.relevance.selected_count == 0

    def test_pp_sec_051_all_dropped_for_token_budget(self, tenant_ids, request_id):
        candidates = [
            make_retrieved_chunk(
                "x" * 8000,
                score=0.9,
                company_id=tenant_ids["companies"]["C1"],
                department_id=tenant_ids["departments"]["C1_D1"],
            )
        ]
        result = PostRetrievalPipeline().process(
            "query",
            _authz(tenant_ids, request_id),
            candidates,
            _metadata(tenant_ids, 1),
            PipelineOptions(top_k=5, max_context_tokens=10),
        )
        assert result.context.text == ""
        assert result.pipeline.dropped_token_budget_count == 1
        assert result.pipeline.top_k_selected == 0

    def test_pp_sec_052_single_chunk_fills_budget(self, tenant_ids, request_id):
        candidates = [
            make_retrieved_chunk(
                f"{index}" + "x" * 200,
                score=0.9 - index * 0.01,
                company_id=tenant_ids["companies"]["C1"],
                department_id=tenant_ids["departments"]["C1_D1"],
                chunk_index=index,
            )
            for index in range(5)
        ]
        # Budget sized to exactly one rendered block, envelope included.
        one_block = assemble_text([render_source_block(candidates[0], citation_id(0))])
        budget = CharEstimateTokenCounter(4).count(one_block)

        result = PostRetrievalPipeline().process(
            "query",
            _authz(tenant_ids, request_id),
            candidates,
            _metadata(tenant_ids, 5),
            PipelineOptions(top_k=5, max_context_tokens=budget),
        )
        assert result.context.block_count == 1
        assert result.pipeline.dropped_token_budget_count == 4

    def test_serialized_payload_is_json_encodable(self, tenant_ids, request_id):
        candidates = [
            make_retrieved_chunk(
                "body",
                score=0.9,
                company_id=tenant_ids["companies"]["C1"],
                department_id=tenant_ids["departments"]["C1_D1"],
            )
        ]
        result = PostRetrievalPipeline().process(
            "query",
            _authz(tenant_ids, request_id),
            candidates,
            _metadata(tenant_ids, 1),
            PipelineOptions(),
        )
        json.dumps(rag_result_to_dict(result), ensure_ascii=False)
