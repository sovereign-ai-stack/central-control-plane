"""Authorization context errors."""


class AuthorizationError(Exception):
    """Base authorization error."""


class MissingAuthorizationContextError(AuthorizationError):
    """Raised when retrieval or downstream code receives no AuthorizationContext."""


class InvalidAuthorizationContextError(AuthorizationError):
    """Raised when AuthorizationContext fails validation."""


class ClientScopeForgeryError(AuthorizationError):
    """Raised when client-supplied tenant scope does not match resolved authorization."""

    http_status = 403
