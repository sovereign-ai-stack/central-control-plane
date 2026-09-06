import pytest

from rag.authorization.context import AuthorizationContext
from rag.authorization.errors import InvalidAuthorizationContextError


def test_invalid_request_id_raises(tenant_ids):
    with pytest.raises(InvalidAuthorizationContextError):
        AuthorizationContext(
            user_id=tenant_ids["users"]["U1"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(tenant_ids["departments"]["C1_D1"],),
            request_id=None,  # type: ignore[arg-type]
        )
