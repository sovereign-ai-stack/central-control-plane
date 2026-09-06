from __future__ import annotations

from uuid import UUID

from rag.authorization.builder import AuthorizationContextBuilder
from rag.authorization.context import AuthorizationContext
from rag.identity.errors import (
    ExpiredTokenError,
    IdentityError,
    IdentityMismatchError,
    InvalidIdentityDataError,
    InvalidTokenError,
    MissingCompanyError,
    MissingIdentityError,
    RevokedTokenError,
    UnknownIdentityError,
    UntrustedIdentityPayloadError,
    UserDisabledError,
)
from rag.identity.provider import IdentityProvider
from rag.identity.store import EntityStatus, utc_now
from rag.identity.types import (
    IdentityContext,
    IdentitySource,
    RagRetrieveRequest,
    TrustedIdentityPayload,
    TrustedIdentityVerifier,
)


class AlwaysTrustedVerifier:
    """Test/dev verifier — accepts all payloads. Do not use in production."""

    def verify(self, payload: TrustedIdentityPayload, request_id: UUID) -> bool:
        return True


class IdentityResolver:
    """Resolve verified IdentityContext from trusted payload and/or bearer token."""

    def __init__(
        self,
        provider: IdentityProvider,
        trusted_verifier: TrustedIdentityVerifier | None = None,
    ) -> None:
        self._provider = provider
        self._trusted_verifier = trusted_verifier or AlwaysTrustedVerifier()

    def resolve(
        self,
        request: RagRetrieveRequest,
        bearer_token: str | None = None,
    ) -> IdentityContext:
        token_identity = (
            self._resolve_from_token(bearer_token, request.request_id)
            if bearer_token
            else None
        )
        trusted_identity = (
            self._resolve_from_trusted(request.trusted_identity, request.request_id)
            if request.trusted_identity is not None
            else None
        )

        if trusted_identity is None and token_identity is None:
            raise MissingIdentityError(
                "Valid trusted identity or bearer token is required"
            )

        if trusted_identity is not None and token_identity is not None:
            if not self._identities_match(trusted_identity, token_identity):
                raise IdentityMismatchError(
                    "Trusted identity and token resolve to different principals"
                )
            return trusted_identity

        identity = trusted_identity or token_identity
        assert identity is not None
        return identity

    def _resolve_from_trusted(
        self,
        payload: TrustedIdentityPayload,
        request_id: UUID,
    ) -> IdentityContext:
        if not self._trusted_verifier.verify(payload, request_id):
            raise UntrustedIdentityPayloadError(
                "Trusted identity payload failed verification"
            )
        self._assert_user_active(payload.user_id)
        self._assert_company_active(payload.company_id)
        department_ids = self._normalize_trusted_departments(payload)
        return IdentityContext(
            user_id=payload.user_id,
            company_id=payload.company_id,
            department_ids=department_ids,
            source=IdentitySource.TRUSTED,
            request_id=request_id,
        )

    def _resolve_from_token(
        self,
        bearer_token: str,
        request_id: UUID,
    ) -> IdentityContext:
        raw = bearer_token.strip()
        if not raw:
            raise InvalidTokenError("Bearer token is empty")

        token_record = self._provider.lookup_token(raw)
        if token_record is None:
            raise InvalidTokenError("Unknown bearer token")

        if token_record.revoked_at is not None:
            raise RevokedTokenError("Bearer token has been revoked")

        if token_record.expires_at is not None and token_record.expires_at <= utc_now():
            raise ExpiredTokenError("Bearer token has expired")

        user = self._provider.get_user(token_record.user_id)
        if user is None:
            raise UnknownIdentityError("Token references unknown user")

        self._assert_user_record_active(user)
        self._assert_company_active(user.company_id)

        try:
            department_ids = self._provider.department_ids_for_user(
                user.id, user.company_id
            )
        except (KeyError, ValueError) as exc:
            raise InvalidIdentityDataError(str(exc)) from exc

        return IdentityContext(
            user_id=user.id,
            company_id=user.company_id,
            department_ids=department_ids,
            source=IdentitySource.TOKEN,
            request_id=request_id,
        )

    def _normalize_trusted_departments(
        self, payload: TrustedIdentityPayload
    ) -> tuple[UUID, ...]:
        user = self._provider.get_user(payload.user_id)
        if user is None:
            raise UnknownIdentityError("Trusted identity references unknown user")
        if user.company_id != payload.company_id:
            raise InvalidIdentityDataError(
                "Trusted identity company_id does not match user record"
            )

        if payload.department_ids:
            try:
                validated = self._provider.department_ids_for_user(
                    payload.user_id, payload.company_id
                )
            except ValueError as exc:
                raise InvalidIdentityDataError(str(exc)) from exc
            requested = set(payload.department_ids)
            allowed = set(validated)
            if not requested.issubset(allowed):
                raise InvalidIdentityDataError(
                    "Trusted identity department_ids exceed user's memberships"
                )
            return tuple(payload.department_ids)

        return self._provider.department_ids_for_user(payload.user_id, payload.company_id)

    def _assert_user_active(self, user_id: UUID) -> None:
        user = self._provider.get_user(user_id)
        if user is None:
            raise UnknownIdentityError("Unknown user")
        self._assert_user_record_active(user)

    def _assert_user_record_active(self, user: object) -> None:
        from rag.identity.store import UserRecord

        if not isinstance(user, UserRecord):
            raise UnknownIdentityError("Unknown user")
        if user.status != EntityStatus.ACTIVE:
            raise UserDisabledError("User account is disabled")

    def _assert_company_active(self, company_id: UUID) -> None:
        status = self._provider.get_company_status(company_id)
        if status is None:
            raise MissingCompanyError("Company not found")
        if status != EntityStatus.ACTIVE.value:
            raise MissingCompanyError("Company is not active")

    @staticmethod
    def _identities_match(left: IdentityContext, right: IdentityContext) -> bool:
        return (
            left.user_id == right.user_id
            and left.company_id == right.company_id
            and set(left.department_ids) == set(right.department_ids)
        )


class IdentityResolutionService:
    """End-to-end: request + token → immutable AuthorizationContext."""

    def __init__(
        self,
        resolver: IdentityResolver,
        builder: AuthorizationContextBuilder | None = None,
    ) -> None:
        self._resolver = resolver
        self._builder = builder or AuthorizationContextBuilder()

    def resolve_authorization(
        self,
        request: RagRetrieveRequest,
        bearer_token: str | None = None,
    ) -> AuthorizationContext:
        identity = self._resolver.resolve(request, bearer_token)
        return self._builder.build(identity)


def identity_error_http_status(error: IdentityError) -> int:
    return error.http_status
