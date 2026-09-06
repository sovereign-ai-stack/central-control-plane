"""Lightweight HTTP-style router for the RAG application boundary."""

from __future__ import annotations

from rag.app.errors import ApiError
from rag.app.handlers.query import RagQueryHandler
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.health import HealthService
from rag.pipeline.serialization import rag_result_to_dict


def _error_body(exc: ApiError, request_id: object) -> dict[str, object]:
    body: dict[str, object] = {
        "error": exc.message,
        "code": exc.code,
        "request_id": str(request_id) if request_id is not None else "",
    }
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is not None:
        # Tells a well-behaved client when to come back instead of hot-looping.
        body["retry_after"] = retry_after
    return body


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    prefix = "Bearer "
    if not authorization_header.startswith(prefix):
        return None
    token = authorization_header[len(prefix) :].strip()
    return token or None


class RagHttpApplication:
    """
    Maps RAG routes to handlers without a web framework.

    - GET  /api/v1/health       -> liveness (cheap, no dependency I/O)
    - GET  /api/v1/health/ready -> readiness (probes dependencies, 503 if down)
    - POST /api/v1/rag/retrieve -> RetrieveHandler (unchanged contract)
    - POST /api/v1/rag/query    -> RagQueryHandler (structured RagResult)
    """

    def __init__(
        self,
        retrieve_handler: RetrieveHandler,
        query_handler: RagQueryHandler | None = None,
        health_service: HealthService | None = None,
    ) -> None:
        self._retrieve = retrieve_handler
        self._query = query_handler
        self._health = health_service

    def dispatch(
        self,
        method: str,
        path: str,
        body: dict[str, object],
        *,
        authorization: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        if method == "GET" and path == "/api/v1/health":
            # Liveness: the process is up. Independent of dependencies, because
            # restarting would not fix a downstream outage.
            if self._health is None:
                return 200, {"status": "ok"}
            return 200, self._health.liveness().to_dict()

        if method == "GET" and path == "/api/v1/health/ready":
            # Readiness: probes every dependency; 503 removes this instance
            # from rotation instead of failing user requests.
            if self._health is None:
                return 200, {"status": "ok", "dependencies": {}}
            report = self._health.readiness()
            return report.http_status, report.to_dict()

        if method == "POST" and path == "/api/v1/rag/retrieve":
            request_id = body.get("request_id")
            try:
                api_request = self._retrieve.parse_request(body)
                trusted_identity = self._retrieve.parse_trusted_identity(body)
                bearer_token = extract_bearer_token(authorization)
                response = self._retrieve.retrieve(
                    api_request,
                    bearer_token=bearer_token,
                    trusted_identity=trusted_identity,
                )
                return 200, response.to_dict()
            except ApiError as exc:
                return exc.http_status, _error_body(exc, request_id)

        if method == "POST" and path == "/api/v1/rag/query":
            if self._query is None:
                return 404, {
                    "error": "not found",
                    "code": "NOT_FOUND",
                    "request_id": "",
                }
            request_id = body.get("request_id")
            try:
                api_request = self._query.parse_request(body)
                trusted_identity = self._query.parse_trusted_identity(body)
                bearer_token = extract_bearer_token(authorization)
                result = self._query.query(
                    api_request,
                    bearer_token=bearer_token,
                    trusted_identity=trusted_identity,
                )
                return 200, rag_result_to_dict(result)
            except ApiError as exc:
                return exc.http_status, _error_body(exc, request_id)

        return 404, {"error": "not found", "code": "NOT_FOUND", "request_id": ""}
