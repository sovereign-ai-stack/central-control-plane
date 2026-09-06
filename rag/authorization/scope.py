from __future__ import annotations

from uuid import UUID

from rag.authorization.context import AuthorizationContext
from rag.authorization.errors import ClientScopeForgeryError


class ClientScopeGuard:
    """Reject client-supplied tenant scope that does not match resolved authorization."""

    @staticmethod
    def assert_company_matches(
        authorization_context: AuthorizationContext,
        client_company_id: UUID | None,
    ) -> None:
        if client_company_id is None:
            return
        if client_company_id != authorization_context.company_id:
            raise ClientScopeForgeryError(
                "Client-supplied company_id does not match resolved authorization"
            )

    @staticmethod
    def assert_department_allowed(
        authorization_context: AuthorizationContext,
        client_department_id: UUID | None,
    ) -> None:
        if client_department_id is None:
            return
        if client_department_id not in authorization_context.allowed_department_ids:
            raise ClientScopeForgeryError(
                "Client-supplied department_id is not in allowed_department_ids"
            )

    @staticmethod
    def assert_ingest_scope(
        authorization_context: AuthorizationContext,
        client_company_id: UUID,
        client_department_id: UUID,
    ) -> None:
        ClientScopeGuard.assert_company_matches(authorization_context, client_company_id)
        ClientScopeGuard.assert_department_allowed(
            authorization_context, client_department_id
        )
