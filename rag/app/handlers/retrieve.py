"""Application handler for POST /rag/retrieve."""

from __future__ import annotations

import time
from uuid import UUID

from rag.app.errors import ApiValidationError
from rag.app.http import map_to_api_error
from rag.app.limits import RequestLimits
from rag.app.rate_limit import RateLimiter
from rag.app.types import (
    RetrievalApiRequest,
    RetrievalApiResponse,
    RetrievalChunkResponse,
    RetrievalContextResponse,
)
from rag.contracts.retrieval import RetrievalOptions, RetrievedChunk
from rag.identity.types import TrustedIdentityPayload
from rag.retrieval.service import RetrievalService

FORBIDDEN_SCOPE_KEYS = frozenset(
    {
        "company_id",
        "department_id",
        "department_ids",
        "allowed_department_ids",
        "document_ids",
        "filters",
        "filter_override",
        "skip_authz",
    }
)


class RetrieveHandler:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        rate_limiter: RateLimiter | None = None,
        request_limits: RequestLimits | None = None,
    ) -> None:
        self._retrieval = retrieval_service
        self._rate_limiter = rate_limiter
        self._limits = request_limits or RequestLimits()

    def retrieve(
        self,
        request: RetrievalApiRequest,
        *,
        bearer_token: str | None = None,
        trusted_identity: TrustedIdentityPayload | None = None,
    ) -> RetrievalApiResponse:
        started = time.perf_counter()
        # Throttle before any expensive work — and before identity resolution,
        # so the auth path is protected too.
        if self._rate_limiter is not None:
            self._rate_limiter.enforce(bearer_token, scope="read")
        self._validate_request(request)
        # Bound input size before identity resolution, NLP, or embedding.
        self._limits.check_query(request.query)
        try:
            result = self._retrieval.search(
                request.query,
                request.request_id,
                bearer_token=bearer_token,
                trusted_identity=trusted_identity,
                options=RetrievalOptions(top_k=request.top_k),
            )
        except Exception as exc:
            raise map_to_api_error(exc) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        chunks = tuple(self._to_public_chunk(chunk) for chunk in result.chunks)
        context = None
        if result.context is not None:
            context = RetrievalContextResponse(
                text=result.context.text,
                char_count=result.context.char_count,
                truncated=result.context.truncated,
            )
        return RetrievalApiResponse(
            request_id=request.request_id,
            chunks=chunks,
            chunk_count=len(chunks),
            latency_ms=elapsed_ms,
            context=context,
        )

    @staticmethod
    def parse_request(body: dict[str, object]) -> RetrievalApiRequest:
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
        if not isinstance(top_k_raw, int):
            raise ApiValidationError("top_k must be an integer")
        return RetrievalApiRequest(
            query=query,
            request_id=UUID(request_id_raw),
            top_k=top_k_raw,
        )

    @staticmethod
    def parse_trusted_identity(body: dict[str, object]) -> TrustedIdentityPayload | None:
        identity = body.get("identity")
        if identity is None:
            return None
        if not isinstance(identity, dict):
            raise ApiValidationError("identity must be an object")
        forbidden = FORBIDDEN_SCOPE_KEYS.intersection(identity.keys()) - {
            "company_id",
            "department_ids",
            "user_id",
        }
        if forbidden:
            raise ApiValidationError(
                "identity object contains unsupported authorization fields"
            )
        user_id = identity.get("user_id")
        company_id = identity.get("company_id")
        department_ids = identity.get("department_ids")
        if not isinstance(user_id, str) or not isinstance(company_id, str):
            raise ApiValidationError("identity requires user_id and company_id")
        if not isinstance(department_ids, list):
            raise ApiValidationError("identity.department_ids must be a list")
        return TrustedIdentityPayload(
            user_id=UUID(user_id),
            company_id=UUID(company_id),
            department_ids=tuple(UUID(value) for value in department_ids),
        )

    @staticmethod
    def _validate_request(request: RetrievalApiRequest) -> None:
        if not request.query.strip():
            raise ApiValidationError("query must not be empty")

    @staticmethod
    def _to_public_chunk(chunk: RetrievedChunk | object) -> RetrievalChunkResponse:
        if not isinstance(chunk, RetrievedChunk):
            raise ApiValidationError("invalid retrieval chunk type")
        return RetrievalChunkResponse(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            content=chunk.content,
            score=chunk.score,
            company_id=chunk.company_id,
            department_id=chunk.department_id,
            chunk_index=chunk.chunk_index,
        )
