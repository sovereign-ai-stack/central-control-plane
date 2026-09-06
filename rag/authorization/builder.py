from __future__ import annotations

from rag.authorization.context import AuthorizationContext
from rag.identity.types import IdentityContext


class AuthorizationContextBuilder:
    """Build immutable AuthorizationContext from verified IdentityContext only."""

    def build(self, identity: IdentityContext) -> AuthorizationContext:
        return AuthorizationContext(
            user_id=identity.user_id,
            company_id=identity.company_id,
            allowed_department_ids=identity.department_ids,
            request_id=identity.request_id,
        )
