from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag.authorization.errors import (
    InvalidAuthorizationContextError,
    MissingAuthorizationContextError,
)


def _validate_uuid(value: UUID, field_name: str) -> None:
    if value is None:
        raise InvalidAuthorizationContextError(f"{field_name} must be a non-null UUID")
    if not isinstance(value, UUID):
        raise InvalidAuthorizationContextError(f"{field_name} must be a UUID")


def _normalize_department_ids(
    department_ids: tuple[UUID, ...] | list[UUID],
) -> tuple[UUID, ...]:
    if isinstance(department_ids, list):
        return tuple(department_ids)
    return department_ids


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Immutable authorization scope for secure retrieval."""

    user_id: UUID
    company_id: UUID
    allowed_department_ids: tuple[UUID, ...]
    request_id: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.user_id, "user_id")
        _validate_uuid(self.company_id, "company_id")
        _validate_uuid(self.request_id, "request_id")
        object.__setattr__(
            self,
            "allowed_department_ids",
            _normalize_department_ids(self.allowed_department_ids),
        )
        for department_id in self.allowed_department_ids:
            _validate_uuid(department_id, "allowed_department_ids[]")

    @property
    def has_department_access(self) -> bool:
        return len(self.allowed_department_ids) > 0


def require_authorization_context(
    authorization_context: AuthorizationContext | None,
) -> AuthorizationContext:
    """Validate that authorization context is present (fail closed)."""
    if authorization_context is None:
        raise MissingAuthorizationContextError(
            "AuthorizationContext is required; retrieval cannot proceed without it"
        )
    return authorization_context
