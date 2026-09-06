"""
Integration tests for the post-retrieval RAG pipeline
(spec 005 PP-001..PP-004, PP-012..PP-013, acceptance §8).
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from tests.rag.conftest import make_ingest_request

from rag.app.errors import ApiValidationError
from rag.app.handlers.query import RagQueryApiRequest
from rag.contracts.retrieval import RetrievalResult, RetrievedContextSummary
from rag.pipeline.config import MAX_CONTEXT_TOKENS, PipelineConfig
from rag.pipeline.pipeline import PostRetrievalPipeline
from rag.pipeline.reranker import LexicalReranker, NoOpReranker
from rag.retrieval.engine import SecureRetrievalEngine


def _ingest(rag_application, tenant_ids, request_id, content, **kwargs):
    return rag_application.ingestion_service.create_document(
        make_ingest_request(tenant_ids, content=content, **kwargs),
        request_id,
        tenant_ids["tokens"]["U1"],
    )


class TestPipelineStages:
    def test_pp_001_end_to_end_produces_rag_result(
        self, rag_application, tenant_ids, request_id
    ):
        created = _ingest(
            rag_application,
            tenant_ids,
            request_id,
            "سیاست مرخصی: مرخصی سالانه برای کارکنان ۲۶ روز است.",
        )
        result = rag_application.rag_orchestrator.execute(
            "مرخصی سالانه", request_id, tenant_ids["tokens"]["U1"]
        )
        assert result.chunks
        assert result.chunks[0].document_id == created.document_id
        assert result.sources
        assert result.provenance
        assert result.context.block_count == len(result.chunks)
        assert result.context.format == "delimited_v1"
        assert result.request_id == request_id

    def test_pp_004_engine_is_called_exactly_once_per_request(
        self, rag_application, tenant_ids, request_id
    ):
        """
        The pipeline never re-queries the corpus: one request produces exactly
        one secure retrieval call, made by the orchestrator.
        """
        _ingest(rag_application, tenant_ids, request_id, "سند برای شمارش فراخوانی")
        empty = RetrievalResult(
            chunks=(),
            context=RetrievedContextSummary(text="", char_count=0, truncated=False),
        )
        with patch.object(
            SecureRetrievalEngine, "search", autospec=True, return_value=empty
        ) as spy:
            result = rag_application.rag_orchestrator.execute(
                "سند برای شمارش فراخوانی", request_id, tenant_ids["tokens"]["U1"]
            )
        assert spy.call_count == 1
        assert result.chunks == ()

    def test_pp_002_empty_retrieval_returns_valid_result(
        self, rag_application, tenant_ids, request_id
    ):
        result = rag_application.rag_orchestrator.execute(
            "هیچ سندی با این عبارت وجود ندارد", request_id, tenant_ids["tokens"]["U1"]
        )
        assert result.chunks == ()
        assert result.context.text == ""
        assert result.relevance.candidate_count == 0
        assert result.identity.company_id == tenant_ids["companies"]["C1"]

    def test_candidate_pool_is_larger_than_top_k(
        self, rag_application, tenant_ids, request_id
    ):
        for index in range(12):
            _ingest(
                rag_application,
                tenant_ids,
                request_id,
                f"سند شماره {index} درباره سیاست مرخصی سالانه کارکنان",
                document_id=uuid4(),
            )
        options = rag_application.pipeline_config.to_options(top_k=3)
        result = rag_application.rag_orchestrator.execute(
            "سیاست مرخصی", request_id, tenant_ids["tokens"]["U1"], options=options
        )
        assert len(result.chunks) == 3
        # Reranking and selection saw a wider pool than the three returned rows.
        assert result.relevance.candidate_count > 3
        assert result.pipeline.top_k_requested == 3
        assert result.pipeline.top_k_selected == 3

    def test_stage_latencies_recorded(self, rag_application, tenant_ids, request_id):
        _ingest(rag_application, tenant_ids, request_id, "سند برای زمان‌سنجی مراحل")
        result = rag_application.rag_orchestrator.execute(
            "سند برای زمان‌سنجی مراحل", request_id, tenant_ids["tokens"]["U1"]
        )
        assert set(result.pipeline.stages) == {
            "authorization",
            "rerank",
            "dedupe",
            "top_k",
            "context",
        }
        assert result.retrieval.latency_ms >= 0


class TestRerankToggle:
    def test_pp_012_noop_by_default(self, rag_application, tenant_ids, request_id):
        _ingest(rag_application, tenant_ids, request_id, "سند پیش‌فرض بدون rerank")
        result = rag_application.rag_orchestrator.execute(
            "سند پیش‌فرض", request_id, tenant_ids["tokens"]["U1"]
        )
        assert result.pipeline.rerank_enabled is False
        assert result.pipeline.rerank_model_id is None
        assert isinstance(rag_application.post_retrieval_pipeline.reranker, NoOpReranker)

    def test_pp_013_metadata_reflects_rerank_option(
        self, rag_application, tenant_ids, request_id
    ):
        _ingest(rag_application, tenant_ids, request_id, "سند برای فعال‌سازی rerank")
        options = rag_application.pipeline_config.to_options(rerank=True)
        result = rag_application.rag_orchestrator.execute(
            "سند برای فعال‌سازی rerank",
            request_id,
            tenant_ids["tokens"]["U1"],
            options=options,
        )
        assert result.pipeline.rerank_enabled is True
        assert result.pipeline.reranked_candidate_count >= 1

    def test_lexical_backend_is_configurable_without_model_download(self):
        config = PipelineConfig(rerank=True, backend="lexical")
        pipeline = PostRetrievalPipeline(config)
        assert isinstance(pipeline.reranker, LexicalReranker)
        assert pipeline.reranker.model_id == "lexical-rerank-v1"

    def test_rerank_reorders_but_keeps_the_same_documents(
        self, rag_application, tenant_ids, request_id
    ):
        _ingest(
            rag_application,
            tenant_ids,
            request_id,
            "کارکنان حق مرخصی سالانه دارند و باید درخواست ثبت کنند.",
        )
        _ingest(
            rag_application,
            tenant_ids,
            request_id,
            "راهنمای فنی سرور و پیکربندی پورت‌ها.",
            document_id=uuid4(),
        )
        pipeline = PostRetrievalPipeline(
            PipelineConfig(rerank=True, backend="lexical")
        )
        orchestrator = type(rag_application.rag_orchestrator)(
            rag_application.retrieval_service,
            pipeline,
            document_store=rag_application.document_store,
        )
        options = pipeline.config.to_options(rerank=True, top_k=5)
        without = rag_application.rag_orchestrator.execute(
            "مرخصی سالانه", request_id, tenant_ids["tokens"]["U1"]
        )
        with_rerank = orchestrator.execute(
            "مرخصی سالانه",
            request_id,
            tenant_ids["tokens"]["U1"],
            options=options,
        )
        assert {c.chunk_id for c in with_rerank.chunks} == {
            c.chunk_id for c in without.chunks
        }
        assert with_rerank.chunks[0].rerank_score is not None


class TestCitationMetadata:
    def test_sources_carry_document_title_and_source(
        self, rag_application, tenant_ids, request_id
    ):
        rag_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids,
                content="سند دارای عنوان برای استناد",
                title="سیاست منابع انسانی",
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        result = rag_application.rag_orchestrator.execute(
            "سند دارای عنوان", request_id, tenant_ids["tokens"]["U1"]
        )
        assert result.sources
        assert result.sources[0].title == "سیاست منابع انسانی"
        assert result.sources[0].source == "test-fixture"

    def test_provenance_positions_match_context_order(
        self, rag_application, tenant_ids, request_id
    ):
        for index in range(3):
            _ingest(
                rag_application,
                tenant_ids,
                request_id,
                f"سند استناد شماره {index} درباره مرخصی",
                document_id=uuid4(),
            )
        result = rag_application.rag_orchestrator.execute(
            "سند استناد", request_id, tenant_ids["tokens"]["U1"]
        )
        positions = [record.position_in_context for record in result.provenance]
        assert positions == sorted(positions)
        text = result.context.text
        offsets = [
            text.index(f'id="{record.citation_id}"') for record in result.provenance
        ]
        assert offsets == sorted(offsets)


class TestApiIntegration:
    def test_http_query_route_returns_rag_result(
        self, rag_application, rag_http_app, tenant_ids, request_id
    ):
        _ingest(rag_application, tenant_ids, request_id, "سند مسیر HTTP برای query")
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/query",
            {
                "query": "سند مسیر HTTP برای query",
                "request_id": str(request_id),
                "top_k": 3,
            },
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 200
        assert body["context"]["format"] == "delimited_v1"
        assert body["chunks"]
        assert body["pipeline"]["rerank_enabled"] is False

    def test_retrieve_route_response_shape_is_unchanged(
        self, rag_application, rag_http_app, tenant_ids, request_id
    ):
        _ingest(rag_application, tenant_ids, request_id, "سازگاری عقب‌رو retrieve")
        status, body = rag_http_app.dispatch(
            "POST",
            "/api/v1/rag/retrieve",
            {
                "query": "سازگاری عقب‌رو retrieve",
                "request_id": str(request_id),
                "top_k": 3,
            },
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 200
        assert set(body) == {"request_id", "chunks", "retrieval", "context"}
        assert set(body["chunks"][0]) == {
            "chunk_id",
            "document_id",
            "content",
            "score",
            "metadata",
        }

    def test_query_route_absent_when_handler_not_wired(
        self, retrieve_handler, request_id
    ):
        from rag.app.router import RagHttpApplication

        app = RagHttpApplication(retrieve_handler)
        status, _body = app.dispatch(
            "POST", "/api/v1/rag/query", {"request_id": str(request_id)}
        )
        assert status == 404

    def test_invalid_top_k_rejected(self, rag_query_handler, tenant_ids, request_id):
        with pytest.raises(ApiValidationError):
            rag_query_handler.query(
                RagQueryApiRequest(query="valid", request_id=request_id, top_k=0),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_empty_query_rejected(self, rag_query_handler, tenant_ids, request_id):
        with pytest.raises(ApiValidationError):
            rag_query_handler.query(
                RagQueryApiRequest(query="   ", request_id=request_id),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_excessive_context_request_is_clamped(
        self, rag_application, rag_query_handler, tenant_ids, request_id
    ):
        _ingest(rag_application, tenant_ids, request_id, "سند محدودیت زمینه")
        result = rag_query_handler.query(
            RagQueryApiRequest(
                query="سند محدودیت زمینه",
                request_id=request_id,
                max_context_tokens=MAX_CONTEXT_TOKENS * 10,
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        # Clamped to the configured ceiling rather than honoured or rejected.
        assert result.context.token_count <= rag_application.pipeline_config.max_context_tokens

    def test_negative_context_budget_rejected(
        self, rag_query_handler, tenant_ids, request_id
    ):
        with pytest.raises(ApiValidationError):
            rag_query_handler.query(
                RagQueryApiRequest(
                    query="valid",
                    request_id=request_id,
                    max_context_tokens=-1,
                ),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
