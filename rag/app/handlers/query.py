"""
Application handler for POST /rag/query — structured RagResult.

Backward compatibility: this is a separate path from `/rag/retrieve`, whose
request and response shapes are unchanged. Callers that need the structured
`RagResult` opt in by calling this endpoint.

The same caller-supplied-scope rejection as `/rag/retrieve` applies: the only
knobs exposed here (`top_k`, `rerank`, `max_context_tokens`) tune result size
and ordering, never authorization scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag.app.errors import ApiValidationError
from rag.app.handlers.retrieve import FORBIDDEN_SCOPE_KEYS, RetrieveHandler
from rag.app.http import map_to_api_error
from rag.app.limits import RequestLimits
from rag.app.rate_limit import RateLimiter
from rag.identity.types import TrustedIdentityPayload
from rag.pipeline.orchestrator import RagOrchestrator
from rag.pipeline.types import RagResult


@dataclass(frozen=True, slots=True)
class RagQueryApiRequest:
    query: str
    request_id: UUID
    top_k: int = 10
    rerank: bool = False
    max_context_tokens: int | None = None


class RagQueryHandler:
    def __init__(
        self,
        orchestrator: RagOrchestrator,
        rate_limiter: RateLimiter | None = None,
        request_limits: RequestLimits | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._rate_limiter = rate_limiter
        self._limits = request_limits or RequestLimits()

    def query(
        self,
        request: RagQueryApiRequest,
        *,
        bearer_token: str | None = None,
        trusted_identity: TrustedIdentityPayload | None = None,
    ) -> RagResult:
        # Throttle before any expensive work, ahead of identity resolution.
        if self._rate_limiter is not None:
            self._rate_limiter.enforce(bearer_token, scope="read")
        self._validate_request(request)
        # Bound input size before identity resolution, NLP, or embedding.
        self._limits.check_query(request.query)
        options = self._orchestrator.config.to_options(
            rerank=request.rerank,
            top_k=request.top_k,
            max_context_tokens=request.max_context_tokens,
        )
        try:
            return self._orchestrator.execute(
                request.query,
                request.request_id,
                bearer_token,
                trusted_identity=trusted_identity,
                options=options,
            )
        except Exception as exc:
            raise map_to_api_error(exc) from exc

    @staticmethod
    def parse_request(body: dict[str, object]) -> RagQueryApiRequest:
        forbidden = FORBIDDEN_SCOPE_KEYS.intersection(body.keys())
        if forbidden:
            raise ApiValidationError(
                "caller-supplied authorization scope is not allowed"
            )
        query = body.get("query")
        if not isinstance(query, str):
            raise ApiValidationError("query is required")
        request_id_raw = body.get("request_id")
        if not isinstance(request_id_raw, str):
            raise ApiValidationError("request_id is required")
        top_k_raw = body.get("top_k", 10)
        if not isinstance(top_k_raw, int) or isinstance(top_k_raw, bool):
            raise ApiValidationError("top_k must be an integer")
        rerank_raw = body.get("rerank", False)
        if not isinstance(rerank_raw, bool):
            raise ApiValidationError("rerank must be a boolean")
        max_tokens_raw = body.get("max_context_tokens")
        if max_tokens_raw is not None and (
            not isinstance(max_tokens_raw, int) or isinstance(max_tokens_raw, bool)
        ):
            raise ApiValidationError("max_context_tokens must be an integer")
        return RagQueryApiRequest(
            query=query,
            request_id=UUID(request_id_raw),
            top_k=top_k_raw,
            rerank=rerank_raw,
            max_context_tokens=max_tokens_raw,
        )

    @staticmethod
    def parse_trusted_identity(body: dict[str, object]) -> TrustedIdentityPayload | None:
        return RetrieveHandler.parse_trusted_identity(body)

    @staticmethod
    def _validate_request(request: RagQueryApiRequest) -> None:
        if not request.query.strip():
            raise ApiValidationError("query must not be empty")
        if request.max_context_tokens is not None and request.max_context_tokens <= 0:
            raise ApiValidationError("max_context_tokens must be positive")
