"""Ingestion authorization."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from rag.authorization.context import AuthorizationContext
from rag.authorization.errors import ClientScopeForgeryError
from rag.authorization.scope import ClientScopeGuard
from rag.identity.provider import IdentityProvider
from rag.ingestion.errors import IngestAuthzDeniedError, IngestValidationError
from rag.ingestion.types import DocumentRecord, DocumentStatus, IngestScope


@runtime_checkable
class PermissionRegistry(Protocol):
    """Ingest permission lookup. Backend-agnostic."""

    def grant_company_wide(self, user_id: UUID) -> None:
        ...

    def revoke_company_wide(self, user_id: UUID) -> None:
        ...

    def is_company_wide(self, user_id: UUID) -> bool:
        ...

    def ping(self) -> bool:
        ...


class IngestPermissionRegistry:
    """
    Users allowed to ingest into any department within their company.

    Process-local; see `SqlitePermissionRegistry` for the durable equivalent.
    """

    def __init__(self) -> None:
        self._company_wide_user_ids: set[UUID] = set()

    def grant_company_wide(self, user_id: UUID) -> None:
        self._company_wide_user_ids.add(user_id)

    def revoke_company_wide(self, user_id: UUID) -> None:
        self._company_wide_user_ids.discard(user_id)

    def is_company_wide(self, user_id: UUID) -> bool:
        return user_id in self._company_wide_user_ids

    def ping(self) -> bool:
        return True


class IngestAuthorizationService:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        permissions: IngestPermissionRegistry | None = None,
    ) -> None:
        self._provider = identity_provider
        self._permissions = permissions or IngestPermissionRegistry()

    @property
    def permissions(self) -> IngestPermissionRegistry:
        return self._permissions

    def authorize_create_scope(
        self,
        authorization_context: AuthorizationContext,
        client_company_id: UUID,
        client_department_id: UUID,
    ) -> IngestScope:
        self._validate_fk(client_company_id, client_department_id)
        if self._permissions.is_company_wide(authorization_context.user_id):
            ClientScopeGuard.assert_company_matches(
                authorization_context, client_company_id
            )
        else:
            ClientScopeGuard.assert_ingest_scope(
                authorization_context, client_company_id, client_department_id
            )
        if not self._can_write_department(
            authorization_context, client_company_id, client_department_id
        ):
            raise IngestAuthzDeniedError(
                "Actor is not authorized to ingest into the target department"
            )
        return IngestScope(
            company_id=client_company_id,
            department_id=client_department_id,
            actor_user_id=authorization_context.user_id,
        )

    def authorize_document_access(
        self,
        authorization_context: AuthorizationContext,
        document: DocumentRecord,
    ) -> None:
        if document.status == DocumentStatus.DELETED:
            raise IngestAuthzDeniedError("Document is deleted")
        self._validate_fk(document.company_id, document.department_id)
        if self._permissions.is_company_wide(authorization_context.user_id):
            ClientScopeGuard.assert_company_matches(
                authorization_context, document.company_id
            )
        else:
            ClientScopeGuard.assert_ingest_scope(
                authorization_context, document.company_id, document.department_id
            )
        if not self._can_write_department(
            authorization_context, document.company_id, document.department_id
        ):
            raise IngestAuthzDeniedError(
                "Actor is not authorized to modify this document"
            )

    def assert_scope_unchanged(
        self,
        document: DocumentRecord,
        client_company_id: UUID,
        client_department_id: UUID,
    ) -> None:
        if (
            client_company_id != document.company_id
            or client_department_id != document.department_id
        ):
            raise ClientScopeForgeryError(
                "Document security scope cannot be changed via update"
            )

    def _can_write_department(
        self,
        authorization_context: AuthorizationContext,
        company_id: UUID,
        department_id: UUID,
    ) -> bool:
        if company_id != authorization_context.company_id:
            return False
        if self._permissions.is_company_wide(authorization_context.user_id):
            return True
        return department_id in authorization_context.allowed_department_ids

    def _validate_fk(self, company_id: UUID, department_id: UUID) -> None:
        if self._provider.get_company_status(company_id) is None:
            raise IngestValidationError("company_id does not exist")
        if not self._provider.department_belongs_to_company(company_id, department_id):
            raise IngestValidationError("department_id does not belong to company_id")
