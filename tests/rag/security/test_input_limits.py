"""
Input size and time limits (audit findings M2, M3, and the M4 memory fix).

Two DoS surfaces on the input side:

- an unbounded query was normalized, tokenized, morphologically processed and
  embedded before anything checked its size
- extraction had size and page caps but no *time* cap, so a pathological PDF
  could burn unbounded CPU inside the parser
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest

from rag.app.errors import (
    ApiAuthenticationError,
    ApiPayloadTooLargeError,
    ApiRateLimitError,
    ApiValidationError,
)
from rag.app.handlers.query import RagQueryApiRequest, RagQueryHandler
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.limits import DEFAULT_MAX_QUERY_CHARS, RequestLimits, load_request_limits
from rag.app.rate_limit import RateLimitConfig, RateLimiter
from rag.app.types import RetrievalApiRequest
from rag.ingestion.extraction.errors import (
    ExtractionLimitError,
    ExtractionTimeoutError,
)
from rag.ingestion.extraction.limits import Deadline, ExtractionLimits
from rag.ingestion.extraction.registry import ExtractorRegistry
from rag.ingestion.extraction.timeout import run_with_timeout
from rag.ingestion.extraction.types import ExtractedDocument, SourceSegment
from rag.ingestion.types import IngestFileRequest
from tests.rag.conftest import make_ingest_request
from tests.rag.pdf_fixtures import build_pdf


class CountingEmbeddingService:
    """Records whether embedding was ever reached."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def embed_query(self, raw_text):
        self.calls += 1
        return self._inner.embed_query(raw_text)


# ---------------------------------------------------------------- M2: query size


class TestQueryLimitConfiguration:
    def test_default_is_applied(self):
        assert RequestLimits().max_query_chars == DEFAULT_MAX_QUERY_CHARS

    def test_shipped_config_loads(self):
        limits = load_request_limits()
        assert limits.max_query_chars > 0

    def test_config_file_is_honoured(self, tmp_path):
        path = tmp_path / "api_limits.yaml"
        path.write_text("api_limits:\n  max_query_chars: 25\n", encoding="utf-8")
        assert load_request_limits(path).max_query_chars == 25

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        assert load_request_limits(tmp_path / "absent.yaml") == RequestLimits()

    def test_invalid_limit_rejected(self):
        with pytest.raises(ApiValidationError):
            RequestLimits(max_query_chars=0).validate()


class TestQueryBoundaryValues:
    @pytest.mark.parametrize("length", [1, 9, 10])
    def test_at_or_below_the_limit_is_accepted(self, length):
        RequestLimits(max_query_chars=10).check_query("x" * length)

    @pytest.mark.parametrize("length", [11, 12, 10_000])
    def test_above_the_limit_is_rejected(self, length):
        with pytest.raises(ApiPayloadTooLargeError):
            RequestLimits(max_query_chars=10).check_query("x" * length)

    def test_limit_is_measured_in_characters_not_bytes(self):
        """A byte limit would silently penalise Persian (multi-byte in UTF-8)."""
        limits = RequestLimits(max_query_chars=10)
        persian = "مرخصی سالانه"  # 12 characters, 22 bytes in UTF-8
        # Persian is ~2 bytes per character, so a byte-based cap would reject
        # roughly half the text a Latin-script caller could send.
        assert len(persian.encode("utf-8")) > len(persian)

        # 10 characters is under the limit even though it exceeds 10 bytes.
        limits.check_query(persian[:10])
        with pytest.raises(ApiPayloadTooLargeError):
            limits.check_query(persian)

    def test_error_is_413(self):
        with pytest.raises(ApiPayloadTooLargeError) as exc_info:
            RequestLimits(max_query_chars=1).check_query("too long")
        assert exc_info.value.http_status == 413
        assert exc_info.value.code == "API_PAYLOAD_TOO_LARGE"

    def test_error_does_not_echo_the_query(self):
        secret = "SECRET" * 100
        with pytest.raises(ApiPayloadTooLargeError) as exc_info:
            RequestLimits(max_query_chars=10).check_query(secret)
        assert "SECRET" not in str(exc_info.value)


@pytest.mark.security
class TestQueryLimitEnforcement:
    def test_retrieve_handler_rejects_oversized_query(
        self, rag_application, tenant_ids, request_id
    ):
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=20),
        )
        with pytest.raises(ApiPayloadTooLargeError):
            handler.retrieve(
                RetrievalApiRequest(query="x" * 500, request_id=request_id),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_query_handler_rejects_oversized_query(
        self, rag_application, tenant_ids, request_id
    ):
        handler = RagQueryHandler(
            rag_application.rag_orchestrator,
            request_limits=RequestLimits(max_query_chars=20),
        )
        with pytest.raises(ApiPayloadTooLargeError):
            handler.query(
                RagQueryApiRequest(query="x" * 500, request_id=request_id),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_embedding_is_never_reached_for_an_oversized_query(
        self, rag_application, tenant_ids, request_id
    ):
        """The whole point: no normalization, tokenization, morphology, or embedding."""
        counter = CountingEmbeddingService(rag_application.embedding_service)
        engine = rag_application.retrieval_service._engine
        engine._embedding = counter

        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=20),
        )
        with pytest.raises(ApiPayloadTooLargeError):
            handler.retrieve(
                RetrievalApiRequest(query="x" * 5_000, request_id=request_id),
                bearer_token=tenant_ids["tokens"]["U1"],
            )
        assert counter.calls == 0

    def test_embedding_is_reached_for_an_acceptable_query(
        self, rag_application, tenant_ids, request_id
    ):
        counter = CountingEmbeddingService(rag_application.embedding_service)
        engine = rag_application.retrieval_service._engine
        engine._embedding = counter

        rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="سند نمونه"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=100),
        )
        handler.retrieve(
            RetrievalApiRequest(query="سند نمونه", request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert counter.calls == 1

    def test_router_returns_413(self, rag_application, tenant_ids, request_id):
        from rag.app.router import RagHttpApplication

        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=20),
        )
        status, body = RagHttpApplication(handler).dispatch(
            "POST",
            "/api/v1/rag/retrieve",
            {"query": "x" * 500, "request_id": str(request_id)},
            authorization=f"Bearer {tenant_ids['tokens']['U1']}",
        )
        assert status == 413
        assert body["code"] == "API_PAYLOAD_TOO_LARGE"


@pytest.mark.security
class TestLimitOrderingDoesNotBypassControls:
    """The new check must not weaken rate limiting or authorization."""

    def test_rate_limiting_still_precedes_the_size_check(
        self, rag_application, request_id, tenant_ids
    ):
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            RateLimiter(RateLimitConfig(requests_per_minute=1, burst=1)),
            RequestLimits(max_query_chars=10),
        )
        request = RetrievalApiRequest(query="x" * 500, request_id=request_id)
        # First oversized request: throttle passes, size check rejects.
        with pytest.raises(ApiPayloadTooLargeError):
            handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U1"])
        # Second: the budget was already spent, so throttling wins.
        with pytest.raises(ApiRateLimitError):
            handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U1"])

    def test_oversized_query_cannot_be_used_to_probe_authorization(
        self, rag_application, request_id
    ):
        """
        An oversized query is rejected the same way regardless of credentials,
        so it reveals nothing about auth state.
        """
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=10),
        )
        request = RetrievalApiRequest(query="x" * 500, request_id=request_id)
        for token in (None, "invalid-token"):
            with pytest.raises(ApiPayloadTooLargeError):
                handler.retrieve(request, bearer_token=token)

    def test_authorization_still_enforced_for_acceptable_queries(
        self, rag_application, request_id
    ):
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=100),
        )
        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(
                RetrievalApiRequest(query="کوتاه", request_id=request_id),
                bearer_token=None,
            )

    def test_empty_query_still_rejected_as_validation(
        self, rag_application, tenant_ids, request_id
    ):
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            request_limits=RequestLimits(max_query_chars=100),
        )
        with pytest.raises(ApiValidationError):
            handler.retrieve(
                RetrievalApiRequest(query="   ", request_id=request_id),
                bearer_token=tenant_ids["tokens"]["U1"],
            )

    def test_default_handler_has_a_limit(self, rag_application, tenant_ids, request_id):
        """A handler built without explicit limits is still bounded."""
        handler = RetrieveHandler(rag_application.retrieval_service)
        with pytest.raises(ApiPayloadTooLargeError):
            handler.retrieve(
                RetrievalApiRequest(
                    query="x" * (DEFAULT_MAX_QUERY_CHARS + 1), request_id=request_id
                ),
                bearer_token=tenant_ids["tokens"]["U1"],
            )


# ------------------------------------------------------------ M3: extraction time


class TestDeadline:
    def test_not_expired_within_budget(self):
        assert Deadline(60.0).expired is False

    def test_expires_after_the_budget(self):
        deadline = Deadline(0.01)
        time.sleep(0.05)
        assert deadline.expired is True
        with pytest.raises(ExtractionTimeoutError):
            deadline.check()

    def test_zero_disables_the_budget(self):
        deadline = Deadline(0.0)
        time.sleep(0.01)
        assert deadline.expired is False
        deadline.check()

    def test_timeout_is_a_limit_error(self):
        """Shares 413 semantics: the document costs more than we will spend."""
        assert issubclass(ExtractionTimeoutError, ExtractionLimitError)
        assert ExtractionTimeoutError("x").http_status == 413


class TestRunWithTimeout:
    def test_returns_the_value_within_budget(self):
        assert run_with_timeout(lambda: 42, 5.0) == 42

    def test_raises_on_overrun(self):
        with pytest.raises(ExtractionTimeoutError):
            run_with_timeout(lambda: time.sleep(2.0), 0.05)

    def test_original_error_is_preserved_not_masked(self):
        def boom():
            raise ValueError("specific failure")

        with pytest.raises(ValueError, match="specific failure"):
            run_with_timeout(boom, 5.0)

    def test_non_positive_timeout_runs_inline(self):
        assert run_with_timeout(lambda: "ok", 0) == "ok"

    def test_worker_is_a_daemon_so_it_cannot_block_shutdown(self):
        import threading

        before = threading.active_count()
        with pytest.raises(ExtractionTimeoutError):
            run_with_timeout(lambda: time.sleep(1.0), 0.05)
        # The orphan is a daemon; the interpreter can still exit.
        assert all(t.daemon for t in threading.enumerate() if t.name == "rag-extraction")
        assert threading.active_count() >= before

    def test_timeout_message_exposes_no_internals(self):
        with pytest.raises(ExtractionTimeoutError) as exc_info:
            run_with_timeout(lambda: time.sleep(2.0), 0.05)
        message = str(exc_info.value)
        assert "Traceback" not in message
        assert "pypdf" not in message.lower()
        assert "/" not in message and "\\" not in message


@pytest.mark.security
class TestExtractionTimeout:
    def test_registry_enforces_the_budget(self):
        class SlowExtractor:
            source_type = "slow"
            supported_extensions = (".slow",)

            def sniff(self, data: bytes) -> bool:
                return data.startswith(b"SLOW")

            def extract(self, data, *, filename=None, deadline=None):
                time.sleep(2.0)
                return ExtractedDocument(text="never", source_type="slow")

        registry = ExtractorRegistry(
            [SlowExtractor()], ExtractionLimits(timeout_seconds=0.05)
        )
        with pytest.raises(ExtractionTimeoutError):
            registry.extract(b"SLOW payload", filename="x.slow")

    def test_registry_recovers_after_a_timeout(self):
        """A timeout must not poison the registry for later requests."""
        calls = {"n": 0}

        class SometimesSlow:
            source_type = "text"
            supported_extensions = (".txt",)

            def sniff(self, data: bytes) -> bool:
                return True

            def extract(self, data, *, filename=None, deadline=None):
                calls["n"] += 1
                if calls["n"] == 1:
                    time.sleep(2.0)
                text = data.decode("utf-8")
                return ExtractedDocument(
                    text=text,
                    source_type="text",
                    segments=(
                        SourceSegment(
                            label="document", ordinal=1, char_start=0, char_end=len(text)
                        ),
                    ),
                )

        registry = ExtractorRegistry(
            [SometimesSlow()], ExtractionLimits(timeout_seconds=0.05)
        )
        with pytest.raises(ExtractionTimeoutError):
            registry.extract(b"first", filename="a.txt")
        # The second call must succeed — resources were released.
        assert registry.extract(b"second", filename="b.txt").text == "second"

    def test_cooperative_deadline_stops_between_pages(self):
        """An already-expired deadline halts before any page is parsed."""
        from rag.ingestion.extraction.pdf import PdfExtractor

        expired = Deadline(0.001)
        time.sleep(0.01)
        with pytest.raises(ExtractionTimeoutError):
            PdfExtractor().extract(build_pdf(["a", "b", "c"]), deadline=expired)

    def test_normal_pdf_is_unaffected(self):
        registry = ExtractorRegistry(limits=ExtractionLimits(timeout_seconds=30.0))
        document = registry.extract(build_pdf(["hello world"]), filename="ok.pdf")
        assert "hello world" in document.text

    def test_timeout_is_configurable(self):
        assert ExtractionLimits().timeout_seconds > 0
        assert ExtractionLimits(timeout_seconds=1.5).timeout_seconds == 1.5

    def test_adapter_without_deadline_parameter_still_works(self):
        """Backward compatibility: the extension point is not broken."""

        class LegacyExtractor:
            source_type = "legacy"
            supported_extensions = (".legacy",)

            def sniff(self, data: bytes) -> bool:
                return data.startswith(b"LEGACY")

            def extract(self, data, *, filename=None):
                text = data.decode("utf-8")
                return ExtractedDocument(
                    text=text,
                    source_type="legacy",
                    segments=(
                        SourceSegment(
                            label="document", ordinal=1, char_start=0, char_end=len(text)
                        ),
                    ),
                )

        registry = ExtractorRegistry([LegacyExtractor()])
        assert registry.extract(b"LEGACY body", filename="x.legacy").text == (
            "LEGACY body"
        )

    def test_other_limits_are_preserved(self):
        """Size, page, and character caps still fire alongside the timeout."""
        registry = ExtractorRegistry(
            limits=ExtractionLimits(max_pages=1, timeout_seconds=30.0)
        )
        with pytest.raises(ExtractionLimitError):
            registry.extract(build_pdf(["one", "two"]), filename="x.pdf")

    def test_authorization_still_precedes_extraction(
        self, rag_application, tenant_ids, request_id
    ):
        """The timeout must not have moved extraction ahead of the auth gate."""
        from rag.ingestion.errors import IngestUnauthorizedError

        calls: list[str] = []

        class CountingRegistry(ExtractorRegistry):
            def extract(self, data, *, filename=None, source_type=None):
                calls.append("extract")
                return super().extract(
                    data, filename=filename, source_type=source_type
                )

        rag_application.ingestion_service._extractors = CountingRegistry()
        with pytest.raises(IngestUnauthorizedError):
            rag_application.ingestion_service.create_document_from_file(
                IngestFileRequest(
                    data=build_pdf(["body"]),
                    company_id=tenant_ids["companies"]["C1"],
                    department_id=tenant_ids["departments"]["C1_D1"],
                    source="fixture",
                    filename="x.pdf",
                    document_id=uuid4(),
                ),
                request_id,
                None,
            )
        assert calls == []


@pytest.mark.security
class TestSinglePageMemoryBound:
    """M4: a single enormous page must not be materialised before the check."""

    def test_projected_size_is_checked_before_appending(self):
        from rag.ingestion.extraction.pdf import PdfExtractor

        huge = "x" * 5_000
        with pytest.raises(ExtractionLimitError):
            PdfExtractor(ExtractionLimits(max_extracted_chars=100)).extract(
                build_pdf([huge])
            )

    def test_limit_fires_on_the_first_oversized_page(self):
        """The cap must trigger on page one, not after accumulating them all."""
        from rag.ingestion.extraction.pdf import PdfExtractor

        pages = ["y" * 1_000 for _ in range(5)]
        with pytest.raises(ExtractionLimitError):
            PdfExtractor(ExtractionLimits(max_extracted_chars=500)).extract(
                build_pdf(pages)
            )

    def test_within_budget_still_extracts(self):
        from rag.ingestion.extraction.pdf import PdfExtractor

        document = PdfExtractor(
            ExtractionLimits(max_extracted_chars=10_000)
        ).extract(build_pdf(["short text"]))
        assert "short text" in document.text
