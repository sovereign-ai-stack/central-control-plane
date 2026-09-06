from uuid import uuid4

import pytest

from rag.authorization.builder import AuthorizationContextBuilder
from rag.identity.errors import (
    ExpiredTokenError,
    InvalidIdentityDataError,
    InvalidTokenError,
    MissingIdentityError,
    RevokedTokenError,
    UserDisabledError,
)
from rag.identity.resolver import identity_error_http_status
from rag.identity.types import IdentitySource, RagRetrieveRequest, TrustedIdentityPayload


class TestIdentityResolver:
    def test_trusted_identity_produces_identity_context(
        self, identity_resolver, tenant_ids, request_id
    ):
        payload = TrustedIdentityPayload(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            department_ids=(tenant_ids["departments"]["C1_D1"],),
        )
        identity = identity_resolver.resolve(
            RagRetrieveRequest(request_id=request_id, trusted_identity=payload)
        )
        assert identity.user_id == tenant_ids["users"]["U1"]
        assert identity.company_id == tenant_ids["companies"]["C1"]
        assert identity.source == IdentitySource.TRUSTED

    def test_token_resolves_same_scope_as_trusted(
        self, identity_resolver, tenant_ids, request_id
    ):
        token_identity = identity_resolver.resolve(
            RagRetrieveRequest(request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        payload = TrustedIdentityPayload(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            department_ids=(tenant_ids["departments"]["C1_D1"],),
        )
        trusted_identity = identity_resolver.resolve(
            RagRetrieveRequest(request_id=request_id, trusted_identity=payload)
        )
        assert token_identity.user_id == trusted_identity.user_id
        assert token_identity.company_id == trusted_identity.company_id
        assert set(token_identity.department_ids) == set(trusted_identity.department_ids)

    def test_invalid_token(self, identity_resolver, tenant_ids, request_id):
        with pytest.raises(InvalidTokenError):
            identity_resolver.resolve(
                RagRetrieveRequest(request_id=request_id),
                bearer_token=tenant_ids["tokens"]["INVALID"],
            )

    def test_expired_token(self, identity_resolver, tenant_ids, request_id):
        with pytest.raises(ExpiredTokenError):
            identity_resolver.resolve(
                RagRetrieveRequest(request_id=request_id),
                bearer_token=tenant_ids["tokens"]["EXPIRED"],
            )

    def test_revoked_token(self, identity_resolver, tenant_ids, request_id):
        with pytest.raises(RevokedTokenError):
            identity_resolver.resolve(
                RagRetrieveRequest(request_id=request_id),
                bearer_token=tenant_ids["tokens"]["REVOKED"],
            )

    def test_disabled_user_via_token(self, identity_store, identity_provider, request_id):
        from rag.identity.resolver import IdentityResolver
        from rag.identity.store import CompanyRecord, DepartmentRecord, EntityStatus, UserRecord

        disabled_user = uuid4()
        company_id = uuid4()
        department_id = uuid4()
        identity_store.register_company(CompanyRecord(id=company_id))
        identity_store.register_department(
            DepartmentRecord(id=department_id, company_id=company_id)
        )
        identity_store.register_user(
            UserRecord(id=disabled_user, company_id=company_id, status=EntityStatus.DISABLED),
            [department_id],
        )
        raw = "token-disabled-user"
        identity_store.register_token(uuid4(), disabled_user, raw)
        resolver = IdentityResolver(identity_provider)
        with pytest.raises(UserDisabledError) as exc:
            resolver.resolve(RagRetrieveRequest(request_id=request_id), bearer_token=raw)
        assert identity_error_http_status(exc.value) == 403

    def test_missing_identity(self, identity_resolver, request_id):
        with pytest.raises(MissingIdentityError):
            identity_resolver.resolve(RagRetrieveRequest(request_id=request_id))

    def test_empty_departments_allowed(self, identity_service, tenant_ids, request_id):
        authz = identity_service.resolve_authorization(
            RagRetrieveRequest(request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U3"],
        )
        assert authz.allowed_department_ids == ()


class TestAuthorizationContextBuilder:
    def test_az_001_and_002(self, identity_resolver, tenant_ids, request_id):
        identity = identity_resolver.resolve(
            RagRetrieveRequest(request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U2"],
        )
        authz = AuthorizationContextBuilder().build(identity)
        assert authz.company_id == identity.company_id
        assert set(authz.allowed_department_ids) == set(identity.department_ids)

    def test_forged_department_list_in_trusted_payload(
        self, identity_resolver, tenant_ids, request_id
    ):
        payload = TrustedIdentityPayload(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            department_ids=(
                tenant_ids["departments"]["C1_D1"],
                tenant_ids["departments"]["C1_D2"],
            ),
        )
        with pytest.raises(InvalidIdentityDataError):
            identity_resolver.resolve(
                RagRetrieveRequest(request_id=request_id, trusted_identity=payload)
            )

    def test_id_sec_005_token_and_trusted_mismatch_rejected(
        self, identity_resolver, tenant_ids, request_id
    ):
        from rag.identity.errors import IdentityMismatchError

        payload = TrustedIdentityPayload(
            user_id=tenant_ids["users"]["U2"],
            company_id=tenant_ids["companies"]["C1"],
            department_ids=(
                tenant_ids["departments"]["C1_D1"],
                tenant_ids["departments"]["C1_D3"],
            ),
        )
        request = RagRetrieveRequest(request_id=request_id, trusted_identity=payload)
        with pytest.raises(IdentityMismatchError):
            identity_resolver.resolve(request, bearer_token=tenant_ids["tokens"]["U1"])
        assert identity_error_http_status(IdentityMismatchError()) == 403
