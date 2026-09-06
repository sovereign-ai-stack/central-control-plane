"""Identity resolution errors — fail closed with HTTP status hints."""

from __future__ import annotations


class IdentityError(Exception):
    """Base identity resolution error."""

    http_status: int = 401


class MissingIdentityError(IdentityError):
    """No trusted identity or token provided."""


class InvalidTokenError(IdentityError):
    """Token is malformed or not found."""


class ExpiredTokenError(IdentityError):
    """Token has expired."""


class RevokedTokenError(IdentityError):
    """Token has been revoked."""


class UnknownIdentityError(IdentityError):
    """User referenced by token does not exist."""


class UserDisabledError(IdentityError):
    """User account is disabled."""

    http_status = 403


class MissingCompanyError(IdentityError):
    """User's company is missing or inactive."""

    http_status = 403


class InvalidIdentityDataError(IdentityError):
    """Identity data failed validation (departments, company consistency)."""

    http_status = 403


class IdentityMismatchError(IdentityError):
    """Trusted identity and token resolve to different principals."""

    http_status = 403


class UntrustedIdentityPayloadError(IdentityError):
    """Trusted identity payload failed verification at the trust boundary."""

    http_status = 401
