import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.authorization.scope import ClientScopeGuard
from rag.identity.types import RagRetrieveRequest, TrustedIdentityPayload


@pytest.mark.security
class TestForgedScope:
    def test_sec_fg_001_forged_company_on_ingest(self, identity_service, tenant_ids, request_id):
        authz = identity_service.resolve_authorization(
            RagRetrieveRequest(request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        with pytest.raises(ClientScopeForgeryError):
            ClientScopeGuard.assert_ingest_scope(
                authz,
                client_company_id=tenant_ids["companies"]["C2"],
                client_department_id=tenant_ids["departments"]["C2_D1"],
            )

    def test_sec_fg_002_forged_department_on_ingest(self, identity_service, tenant_ids, request_id):
        authz = identity_service.resolve_authorization(
            RagRetrieveRequest(request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        with pytest.raises(ClientScopeForgeryError):
            ClientScopeGuard.assert_ingest_scope(
                authz,
                client_company_id=tenant_ids["companies"]["C1"],
                client_department_id=tenant_ids["departments"]["C1_D2"],
            )

    def test_sec_fg_003_forged_company_in_trusted_identity_rejected(
        self, identity_resolver, tenant_ids, request_id
    ):
        payload = TrustedIdentityPayload(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C2"],
            department_ids=(tenant_ids["departments"]["C2_D1"],),
        )
        request = RagRetrieveRequest(
            request_id=request_id,
            trusted_identity=payload,
        )
        from rag.identity.errors import InvalidIdentityDataError

        with pytest.raises(InvalidIdentityDataError):
            identity_resolver.resolve(request)

    def test_sec_fg_003_token_scope_used_not_forged_trusted_company(
        self, identity_service, tenant_ids, request_id
    ):
        authz = identity_service.resolve_authorization(
            RagRetrieveRequest(request_id=request_id),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert authz.company_id == tenant_ids["companies"]["C1"]
        ClientScopeGuard.assert_company_matches(
            authz, client_company_id=tenant_ids["companies"]["C1"]
        )
