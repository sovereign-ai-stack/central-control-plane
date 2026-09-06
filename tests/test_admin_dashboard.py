import pytest
from tests.conftest import TestingSessionLocal
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.models.user import UserModel
from datetime import datetime, timezone


def test_admin_dashboard_and_limits(client, auth_headers):
    # 1. Test Dashboard endpoint
    res = client.get("/api/admin/dashboard", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "role" in data
    assert "totalUsers" in data
    assert "maxRps" in data
    assert "workspaceTokenLimit" in data
    assert data["role"] == "super_admin"

    # 2. Test Overview endpoint
    res_ov = client.get("/api/admin/overview", headers=auth_headers)
    assert res_ov.status_code == 200
    assert res_ov.json()["role"] == "super_admin"

    # 3. Test Usage Limits endpoint
    res_lim = client.get("/api/usage-limits", headers=auth_headers)
    assert res_lim.status_code == 200
    lim_data = res_lim.json()
    assert "maxInputChars" in lim_data
    assert "maxOutputTokens" in lim_data
    assert "totalTokensUsed" in lim_data
    assert "totalTokenLimit" in lim_data
