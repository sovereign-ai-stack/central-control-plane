"""Public application/API errors."""

from __future__ import annotations


class ApiError(Exception):
    code: str = "API_ERROR"
    http_status: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ApiValidationError(ApiError):
    code = "API_VALIDATION_ERROR"
    http_status = 400


class ApiAuthenticationError(ApiError):
    code = "API_AUTHENTICATION_ERROR"
    http_status = 401


class ApiAuthorizationError(ApiError):
    code = "API_AUTHORIZATION_ERROR"
    http_status = 403


class ApiPayloadTooLargeError(ApiError):
    """Input exceeds a configured size limit."""

    code = "API_PAYLOAD_TOO_LARGE"
    http_status = 413


class ApiRateLimitError(ApiError):
    """Caller exceeded its request budget, or the service is at capacity."""

    code = "API_RATE_LIMITED"
    http_status = 429

    def __init__(self, message: str, *, retry_after: int = 1) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ApiRetrievalError(ApiError):
    code = "API_RETRIEVAL_ERROR"
    http_status = 503
