from __future__ import annotations

from rag.authorization.errors import (
    AuthorizationError,
    ClientScopeForgeryError,
    InvalidAuthorizationContextError,
    MissingAuthorizationContextError,
)


def authorization_error_http_status(error: AuthorizationError) -> int:
    if isinstance(error, MissingAuthorizationContextError):
        return 401
    if isinstance(error, (InvalidAuthorizationContextError, ClientScopeForgeryError)):
        return 403
    return 403
