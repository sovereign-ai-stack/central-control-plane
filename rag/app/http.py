"""Map internal errors to public API errors."""

from __future__ import annotations

from rag.app.errors import (
    ApiAuthenticationError,
    ApiAuthorizationError,
    ApiError,
    ApiRetrievalError,
    ApiValidationError,
)
from rag.authorization.errors import AuthorizationError, ClientScopeForgeryError
from rag.embedding.errors import EmbeddingError
from rag.identity.errors import IdentityError
from rag.pipeline.errors import (
    PipelineError,
    PipelineValidationError,
    RerankContractViolationError,
    UnauthorizedChunkInPipelineError,
)
from rag.retrieval.errors import (
    RetrievalDimensionMismatchError,
    RetrievalError,
    RetrievalModelMismatchError,
    RetrievalValidationError,
)


def map_to_api_error(error: Exception) -> ApiError:
    if isinstance(error, ApiError):
        return error
    if isinstance(error, (RetrievalValidationError, PipelineValidationError)):
        return ApiValidationError(str(error))
    if isinstance(
        error, (RerankContractViolationError, UnauthorizedChunkInPipelineError)
    ):
        # Fail closed: never leak which chunks or which contract was violated.
        return ApiRetrievalError("retrieval pipeline integrity error")
    if isinstance(error, (RetrievalDimensionMismatchError, RetrievalModelMismatchError)):
        return ApiRetrievalError("retrieval vector compatibility error")
    if isinstance(error, (RetrievalError, EmbeddingError, PipelineError)):
        return ApiRetrievalError("retrieval service unavailable")
    if isinstance(error, ClientScopeForgeryError):
        return ApiAuthorizationError("authorization scope rejected")
    if isinstance(error, AuthorizationError):
        return ApiAuthorizationError("authorization failed")
    if isinstance(error, IdentityError):
        return ApiAuthenticationError("authentication failed")
    return ApiRetrievalError("internal service error")
