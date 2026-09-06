"""Retrieval service — identity resolution before secure search."""

from __future__ import annotations

from uuid import UUID

from rag.authorization.context import AuthorizationContext
from rag.contracts.retrieval import RetrievalOptions, RetrievalResult
from rag.identity.errors import MissingIdentityError
from rag.identity.resolver import IdentityResolutionService
from rag.identity.types import RagRetrieveRequest, TrustedIdentityPayload
from rag.retrieval.engine import SecureRetrievalEngine


class RetrievalService:
    def __init__(
        self,
        identity_service: IdentityResolutionService,
        engine: SecureRetrievalEngine,
    ) -> None:
        self._identity = identity_service
        self._engine = engine

    def search(
        self,
        query: str,
        request_id: UUID,
        bearer_token: str | None = None,
        *,
        trusted_identity: TrustedIdentityPayload | None = None,
        options: RetrievalOptions | None = None,
    ) -> RetrievalResult:
        _authz, result = self.search_with_context(
            query,
            request_id,
            bearer_token,
            trusted_identity=trusted_identity,
            options=options,
        )
        return result

    def search_with_context(
        self,
        query: str,
        request_id: UUID,
        bearer_token: str | None = None,
        *,
        trusted_identity: TrustedIdentityPayload | None = None,
        options: RetrievalOptions | None = None,
    ) -> tuple[AuthorizationContext, RetrievalResult]:
        """
        Same identity-first path as `search`, also returning the resolved context.

        The post-retrieval pipeline needs the server-resolved
        `AuthorizationContext` for L4 re-validation and result identity metadata.
        The context is produced here, never accepted from a caller.
        """
        authz = self._resolve_authz(
            request_id,
            bearer_token,
            trusted_identity=trusted_identity,
            query=query,
        )
        return authz, self._engine.search(query, authz, options)

    def _resolve_authz(
        self,
        request_id: UUID,
        bearer_token: str | None,
        *,
        trusted_identity: TrustedIdentityPayload | None = None,
        query: str = "",
    ) -> AuthorizationContext:
        if not bearer_token and trusted_identity is None:
            raise MissingIdentityError("Authentication required")
        return self._identity.resolve_authorization(
            RagRetrieveRequest(
                request_id=request_id,
                query=query,
                trusted_identity=trusted_identity,
            ),
            bearer_token=bearer_token,
        )
