"""
Rate limiting and concurrency capping tests (audit finding H5).

The gap: nothing throttled anything, so one authenticated caller could saturate
embedding CPU and exhaust the vector store's connections. These cover the token
bucket itself, enforcement at every handler boundary, the concurrency cap, and
the properties that keep the limiter from becoming a liability of its own
(bounded memory, no credentials retained).
"""

from __future__ import annotations

import threading
from uuid import uuid4

import pytest

from rag.app.errors import ApiRateLimitError
from rag.app.handlers.query import RagQueryApiRequest, RagQueryHandler
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.rate_limit import (
    ANONYMOUS_KEY,
    ConcurrencyLimiter,
    RateLimitConfig,
    RateLimiter,
    TokenBucket,
    credential_key,
    load_rate_limit_config,
)
from rag.app.types import RetrievalApiRequest
from rag.ingestion.types import IngestFileRequest
from tests.rag.conftest import STUB_EMBEDDING_CONFIG, make_ingest_request


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def limiter(clock: FakeClock, **overrides) -> RateLimiter:
    defaults = {
        "requests_per_minute": 60,
        "burst": 60,
        "ingest_requests_per_minute": 6,
        "ingest_burst": 6,
        "anonymous_requests_per_minute": 6,
        "anonymous_burst": 6,
    }
    defaults.update(overrides)
    return RateLimiter(RateLimitConfig(**defaults), clock=clock)


class TestTokenBucket:
    def test_allows_up_to_capacity(self):
        bucket = TokenBucket(capacity=3, refill_per_second=1, now=0.0)
        assert all(bucket.consume(0.0).allowed for _ in range(3))

    def test_denies_beyond_capacity(self):
        bucket = TokenBucket(capacity=2, refill_per_second=1, now=0.0)
        bucket.consume(0.0)
        bucket.consume(0.0)
        assert bucket.consume(0.0).allowed is False

    def test_refills_over_time(self):
        bucket = TokenBucket(capacity=2, refill_per_second=1, now=0.0)
        bucket.consume(0.0)
        bucket.consume(0.0)
        assert bucket.consume(0.0).allowed is False
        assert bucket.consume(1.0).allowed is True

    def test_refill_is_capped_at_capacity(self):
        bucket = TokenBucket(capacity=2, refill_per_second=1, now=0.0)
        # A long idle period must not accumulate unlimited burst.
        assert bucket.consume(1_000.0).allowed
        assert bucket.consume(1_000.0).allowed
        assert bucket.consume(1_000.0).allowed is False

    def test_retry_after_is_rounded_up(self):
        bucket = TokenBucket(capacity=1, refill_per_second=1, now=0.0)
        bucket.consume(0.0)
        decision = bucket.consume(0.5)
        assert decision.allowed is False
        # Never advertise a retry that would still be rejected.
        assert decision.retry_after >= 1

    def test_clock_going_backwards_grants_nothing(self):
        bucket = TokenBucket(capacity=1, refill_per_second=1, now=100.0)
        bucket.consume(100.0)
        assert bucket.consume(0.0).allowed is False


class TestCredentialKeying:
    def test_key_is_a_hash_not_the_token(self):
        token = "tok_secret_value"
        key = credential_key(token)
        assert token not in key
        assert key != token

    def test_same_token_maps_to_the_same_bucket(self):
        assert credential_key("tok_a") == credential_key("tok_a")

    def test_different_tokens_are_isolated(self):
        assert credential_key("tok_a") != credential_key("tok_b")

    def test_missing_credential_uses_the_anonymous_bucket(self):
        assert credential_key(None) == ANONYMOUS_KEY
        assert credential_key("") == ANONYMOUS_KEY

    def test_limiter_never_retains_the_raw_token(self):
        clock = FakeClock()
        rate_limiter = limiter(clock)
        rate_limiter.check("tok_super_secret")
        assert "tok_super_secret" not in str(rate_limiter.__dict__)


class TestPerCredentialIsolation:
    def test_one_caller_cannot_exhaust_anothers_budget(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, requests_per_minute=2, burst=2)
        for _ in range(2):
            assert rate_limiter.check("tok_noisy").allowed
        assert rate_limiter.check("tok_noisy").allowed is False
        # A different caller is unaffected.
        assert rate_limiter.check("tok_quiet").allowed is True

    def test_scopes_have_separate_budgets(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, ingest_requests_per_minute=1, ingest_burst=1)
        assert rate_limiter.check("tok", scope="ingest").allowed
        assert rate_limiter.check("tok", scope="ingest").allowed is False
        # Heavy ingestion must not starve retrieval.
        assert rate_limiter.check("tok", scope="read").allowed is True

    def test_anonymous_has_its_own_smaller_budget(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, anonymous_requests_per_minute=1, anonymous_burst=1)
        assert rate_limiter.check(None).allowed
        assert rate_limiter.check(None).allowed is False
        assert rate_limiter.check("tok_authenticated").allowed is True


class TestLimiterMemoryBounds:
    def test_tracked_keys_are_bounded(self):
        """The limiter must not become a memory-exhaustion vector itself."""
        clock = FakeClock()
        rate_limiter = limiter(clock, max_tracked_keys=50)
        for index in range(500):
            rate_limiter.check(f"tok_{index}")
        assert rate_limiter.tracked_keys <= 50

    def test_eviction_is_least_recently_used(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, max_tracked_keys=2, requests_per_minute=1, burst=1)
        rate_limiter.check("tok_a")
        rate_limiter.check("tok_b")
        rate_limiter.check("tok_a")  # refresh a
        rate_limiter.check("tok_c")  # evicts b
        # a is still tracked, so it is still limited.
        assert rate_limiter.check("tok_a").allowed is False

    def test_reset_clears_state(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, requests_per_minute=1, burst=1)
        rate_limiter.check("tok")
        assert rate_limiter.check("tok").allowed is False
        rate_limiter.reset()
        assert rate_limiter.check("tok").allowed is True


class TestEnforcement:
    def test_enforce_raises_with_retry_after(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, requests_per_minute=1, burst=1)
        rate_limiter.enforce("tok")
        with pytest.raises(ApiRateLimitError) as exc_info:
            rate_limiter.enforce("tok")
        assert exc_info.value.http_status == 429
        assert exc_info.value.retry_after >= 1

    def test_disabled_limiter_allows_everything(self):
        clock = FakeClock()
        rate_limiter = RateLimiter(
            RateLimitConfig(enabled=False, requests_per_minute=1, burst=1), clock=clock
        )
        for _ in range(100):
            rate_limiter.enforce("tok")

    def test_error_message_carries_no_credential(self):
        clock = FakeClock()
        rate_limiter = limiter(clock, requests_per_minute=1, burst=1)
        rate_limiter.enforce("tok_secret")
        with pytest.raises(ApiRateLimitError) as exc_info:
            rate_limiter.enforce("tok_secret")
        assert "tok_secret" not in str(exc_info.value)


@pytest.mark.security
class TestHandlerEnforcement:
    def test_retrieve_handler_throttles(self, rag_application, request_id, tenant_ids):
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            RateLimiter(RateLimitConfig(requests_per_minute=1, burst=1)),
        )
        request = RetrievalApiRequest(query="q", request_id=request_id, top_k=5)
        handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U1"])
        with pytest.raises(ApiRateLimitError):
            handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U1"])

    def test_query_handler_throttles(self, rag_application, request_id, tenant_ids):
        handler = RagQueryHandler(
            rag_application.rag_orchestrator,
            RateLimiter(RateLimitConfig(requests_per_minute=1, burst=1)),
        )
        request = RagQueryApiRequest(query="q", request_id=request_id, top_k=5)
        handler.query(request, bearer_token=tenant_ids["tokens"]["U1"])
        with pytest.raises(ApiRateLimitError):
            handler.query(request, bearer_token=tenant_ids["tokens"]["U1"])

    def test_ingestion_throttles(self, identity_store, ingest_permissions, tenant_ids):
        from rag.app.factory import RagApplication

        app = RagApplication.build_in_memory(
            identity_store,
            ingest_permissions=ingest_permissions,
            rate_limit_config=RateLimitConfig(
                ingest_requests_per_minute=1, ingest_burst=1
            ),
            embedding_config=STUB_EMBEDDING_CONFIG,
        )
        app.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content="اول", document_id=uuid4()),
            uuid4(),
            tenant_ids["tokens"]["U1"],
        )
        with pytest.raises(ApiRateLimitError):
            app.ingestion_service.create_document(
                make_ingest_request(tenant_ids, content="دوم", document_id=uuid4()),
                uuid4(),
                tenant_ids["tokens"]["U1"],
            )

    def test_throttle_precedes_extraction(
        self, identity_store, ingest_permissions, tenant_ids
    ):
        """A throttled upload must never reach the file parser."""
        from rag.app.factory import RagApplication
        from rag.ingestion.extraction.registry import ExtractorRegistry
        from tests.rag.pdf_fixtures import build_pdf

        calls: list[str] = []

        class CountingRegistry(ExtractorRegistry):
            def extract(self, data, *, filename=None, source_type=None):
                calls.append("extract")
                return super().extract(
                    data, filename=filename, source_type=source_type
                )

        app = RagApplication.build_in_memory(
            identity_store,
            ingest_permissions=ingest_permissions,
            rate_limit_config=RateLimitConfig(
                ingest_requests_per_minute=1, ingest_burst=1
            ),
            embedding_config=STUB_EMBEDDING_CONFIG,
        )
        app.ingestion_service._extractors = CountingRegistry()

        def upload():
            return app.ingestion_service.create_document_from_file(
                IngestFileRequest(
                    data=build_pdf(["body text"]),
                    company_id=tenant_ids["companies"]["C1"],
                    department_id=tenant_ids["departments"]["C1_D1"],
                    source="rate-limit-fixture",
                    filename="a.pdf",
                    document_id=uuid4(),
                ),
                uuid4(),
                tenant_ids["tokens"]["U1"],
            )

        upload()
        assert len(calls) == 1
        with pytest.raises(ApiRateLimitError):
            upload()
        assert len(calls) == 1  # parser never ran for the throttled request

    def test_throttle_precedes_authentication(self, rag_application, request_id):
        """
        An invalid token is throttled too, so the auth path itself is protected
        from brute force.
        """
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            RateLimiter(RateLimitConfig(anonymous_requests_per_minute=1,
                                        anonymous_burst=1)),
        )
        request = RetrievalApiRequest(query="q", request_id=request_id)
        from rag.app.errors import ApiAuthenticationError

        with pytest.raises(ApiAuthenticationError):
            handler.retrieve(request, bearer_token=None)
        with pytest.raises(ApiRateLimitError):
            handler.retrieve(request, bearer_token=None)

    def test_one_tenant_cannot_throttle_another(
        self, rag_application, request_id, tenant_ids
    ):
        handler = RetrieveHandler(
            rag_application.retrieval_service,
            RateLimiter(RateLimitConfig(requests_per_minute=1, burst=1)),
        )
        request = RetrievalApiRequest(query="q", request_id=request_id, top_k=5)
        handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U1"])
        with pytest.raises(ApiRateLimitError):
            handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U1"])
        # A different tenant's caller is unaffected — no cross-tenant denial.
        handler.retrieve(request, bearer_token=tenant_ids["tokens"]["U2"])


@pytest.mark.security
class TestRouterResponse:
    def test_throttled_request_returns_429_with_retry_after(
        self, rag_application, request_id, tenant_ids
    ):
        from rag.app.router import RagHttpApplication

        handler = RetrieveHandler(
            rag_application.retrieval_service,
            RateLimiter(RateLimitConfig(requests_per_minute=1, burst=1)),
        )
        app = RagHttpApplication(handler)
        body = {"query": "q", "request_id": str(request_id), "top_k": 3}
        auth = f"Bearer {tenant_ids['tokens']['U1']}"

        assert app.dispatch("POST", "/api/v1/rag/retrieve", body, authorization=auth)[0] == 200
        status, payload = app.dispatch(
            "POST", "/api/v1/rag/retrieve", body, authorization=auth
        )
        assert status == 429
        assert payload["code"] == "API_RATE_LIMITED"
        assert payload["retry_after"] >= 1

    def test_health_checks_are_not_throttled(self, rag_http_app):
        # Infrastructure probes must keep working under load.
        for _ in range(50):
            assert rag_http_app.dispatch("GET", "/api/v1/health", {})[0] == 200


class TestConcurrencyLimiter:
    def test_permits_up_to_the_cap(self):
        cap = ConcurrencyLimiter(max_concurrent=2, wait_seconds=0.1)
        with cap, cap:
            pass

    def test_rejects_beyond_the_cap(self):
        cap = ConcurrencyLimiter(max_concurrent=1, wait_seconds=0.05)
        with cap, pytest.raises(ApiRateLimitError):
            cap.__enter__()

    def test_slot_is_released_on_exception(self):
        cap = ConcurrencyLimiter(max_concurrent=1, wait_seconds=0.05)
        with pytest.raises(ValueError), cap:
            raise ValueError("boom")
        # The slot must be free again, not leaked.
        with cap:
            pass

    def test_rejects_invalid_cap(self):
        with pytest.raises(ValueError):
            ConcurrencyLimiter(max_concurrent=0)

    def test_embedding_service_honours_the_cap(self, stub_embedding_model):
        """The cap applies at the single chokepoint every caller passes through."""
        from rag.embedding.preprocessor import EmbeddingPreprocessor
        from rag.embedding.service import EmbeddingService

        blocked: list[bool] = []
        released = threading.Event()
        entered = threading.Event()

        cap = ConcurrencyLimiter(max_concurrent=1, wait_seconds=0.05)
        service = EmbeddingService(
            stub_embedding_model, EmbeddingPreprocessor(), concurrency_limiter=cap
        )

        def hold():
            with cap:
                entered.set()
                released.wait(timeout=2)

        holder = threading.Thread(target=hold)
        holder.start()
        entered.wait(timeout=2)
        try:
            service.embed_query("متن")
            blocked.append(False)
        except ApiRateLimitError:
            blocked.append(True)
        finally:
            released.set()
            holder.join(timeout=2)

        assert blocked == [True]

    def test_embedding_works_without_a_limiter(self, embedding_service):
        assert embedding_service.embed_query("متن").vector is not None


class TestConfiguration:
    def test_shipped_config_is_enabled(self):
        config = load_rate_limit_config()
        assert config.enabled is True
        assert config.burst >= config.requests_per_minute

    def test_ingest_budget_is_smaller_than_read(self):
        config = load_rate_limit_config()
        assert config.ingest_requests_per_minute < config.requests_per_minute

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        assert load_rate_limit_config(tmp_path / "absent.yaml") == RateLimitConfig()

    @pytest.mark.parametrize(
        "overrides",
        [
            {"requests_per_minute": 0},
            {"burst": 0},
            {"ingest_requests_per_minute": -1},
            {"max_tracked_keys": 0},
            {"max_concurrent_embeddings": 0},
            {"requests_per_minute": 100, "burst": 10},
            {"embedding_wait_seconds": -1.0},
        ],
    )
    def test_invalid_config_rejected(self, overrides):
        from rag.app.errors import ApiValidationError

        base = {"requests_per_minute": 60, "burst": 60}
        base.update(overrides)
        with pytest.raises(ApiValidationError):
            RateLimitConfig(**base).validate()

    def test_config_file_is_loaded(self, tmp_path):
        path = tmp_path / "rate_limit.yaml"
        path.write_text(
            "rate_limit:\n  enabled: false\n  requests_per_minute: 5\n  burst: 10\n",
            encoding="utf-8",
        )
        config = load_rate_limit_config(path)
        assert config.enabled is False
        assert config.requests_per_minute == 5

    def test_application_wires_a_limiter(self, rag_application):
        assert rag_application.rate_limiter is not None
        assert rag_application.rate_limiter.config.enabled is True


class TestThreadSafety:
    def test_concurrent_checks_do_not_oversubscribe(self):
        """Under contention the bucket must not hand out more than capacity."""
        rate_limiter = RateLimiter(RateLimitConfig(requests_per_minute=60, burst=60))
        allowed: list[bool] = []
        lock = threading.Lock()

        def worker():
            decision = rate_limiter.check("tok_shared")
            with lock:
                allowed.append(decision.allowed)

        threads = [threading.Thread(target=worker) for _ in range(120)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 60 tokens of burst; refill over the test's duration is negligible.
        assert sum(allowed) <= 62
        assert sum(allowed) >= 55
