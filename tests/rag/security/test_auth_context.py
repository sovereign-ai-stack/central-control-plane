import inspect

import pytest

from rag.authorization.context import AuthorizationContext, require_authorization_context
from rag.authorization.errors import MissingAuthorizationContextError
from rag.authorization.http import authorization_error_http_status
from rag.contracts.retrieval import AuthGuardedStubRetriever, SecureRetriever


@pytest.mark.security
class TestAuthContext:
    def test_sec_au_001_missing_authorization_context(self):
        with pytest.raises(MissingAuthorizationContextError):
            require_authorization_context(None)

    def test_sec_au_002_null_context_maps_to_401(self):
        with pytest.raises(MissingAuthorizationContextError) as exc:
            require_authorization_context(None)
        assert authorization_error_http_status(exc.value) == 401

    def test_sec_au_008_empty_allowed_departments_is_valid(self, tenant_ids, request_id):
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U3"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(),
            request_id=request_id,
        )
        assert authz.allowed_department_ids == ()
        assert authz.has_department_access is False

    def test_authorization_context_is_immutable(self, tenant_ids, request_id):
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        with pytest.raises(AttributeError):
            authz.company_id = tenant_ids["companies"]["C2"]  # type: ignore[misc]


@pytest.mark.security
class TestRetrievalContractAuth:
    """SEC-API-* — contract enforcement without vector store / retrieval impl."""

    def test_sec_api_001_search_without_authz_raises(self):
        retriever = AuthGuardedStubRetriever()
        with pytest.raises(MissingAuthorizationContextError):
            retriever.search("query")

    def test_sec_api_002_arbitrary_filters_rejected(self, tenant_ids, request_id):
        retriever = AuthGuardedStubRetriever()
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        with pytest.raises(TypeError):
            retriever.search(
                "query",
                authz,
                filters={"company_id": str(tenant_ids["companies"]["C2"])},
            )

    def test_sec_api_003_company_kwarg_rejected(self, tenant_ids, request_id):
        retriever = AuthGuardedStubRetriever()
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        with pytest.raises(TypeError):
            retriever.search("query", authz, company_id=tenant_ids["companies"]["C2"])

    def test_sec_api_004_department_kwarg_rejected(self, tenant_ids, request_id):
        retriever = AuthGuardedStubRetriever()
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        with pytest.raises(TypeError):
            retriever.search(
                "query",
                authz,
                department_id=tenant_ids["departments"]["C1_D2"],
            )

    def test_sec_api_005_mandatory_authz_before_stub_retrieval(self, tenant_ids, request_id):
        retriever = AuthGuardedStubRetriever()
        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=request_id,
        )
        result = retriever.search("query", authz)
        assert result.chunks == ()

    def test_secure_retriever_protocol_signature(self):
        signature = inspect.signature(SecureRetriever.search)
        params = list(signature.parameters)
        assert params == ["self", "query", "authorization_context", "options"]
