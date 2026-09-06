import pytest
import json
from datetime import datetime, timezone
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.models.user import UserModel
from tests.conftest import TestingSessionLocal


def test_user_quota_exhaustion(client, auth_headers):
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. Create a user with very small token limit (50 tokens)
    test_user = UserModel(
        id="u_quota_test",
        email="quota_user@test.local",
        name="کاربر سهمیه",
        password="password",
        role="user",
        organization_id=None,
        team_id=None,
        is_active=True,
        used_tokens=0,
        token_limit=50,
        created_at=now,
    )
    db.add(test_user)
    db.commit()
    db.close()

    # Login as this user
    login_res = client.post("/api/auth/login", json={"email": "quota_user@test.local", "password": "password"})
    assert login_res.status_code == 200
    user_token = login_res.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. First request when quota remains (used 0 < limit 50)
    chat_payload = {
        "message": "سلام",
        "conversation_id": "conv_quota_1",
        "language": "fa",
        "use_rag": False,
    }
    res = client.post("/api/chat", json=chat_payload, headers=user_headers)
    assert res.status_code == 200
    events = res.text.strip().split("\n\n")
    event_types = [e for e in events if "event:" in e]
    assert any("event: delta" in e or "event: complete" in e for e in event_types)

    # Verify user consumed tokens in database
    db = TestingSessionLocal()
    u = db.query(UserModel).filter(UserModel.id == "u_quota_test").first()
    assert u.used_tokens > 0
    
    # Manually set used_tokens to equal limit (exhausted)
    u.used_tokens = 50
    db.commit()
    db.close()

    # 3. Next request when quota is exhausted
    res_exceeded = client.post("/api/chat", json=chat_payload, headers=user_headers)
    assert res_exceeded.status_code == 200
    text_output = res_exceeded.text
    assert "quota_exceeded" in text_output
    assert "اتمام سهمیه کاربری" in text_output or "Personal Quota Exceeded" in text_output


def test_team_quota_exhaustion(client):
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).isoformat()
    
    # Create Organization & Team with tiny token limit (80 tokens)
    org = OrganizationModel(
        id="org_quota_team_test",
        name="سازمان تست تیم",
        code="QTM",
        token_limit=100000,
        created_at=now,
    )
    team = TeamModel(
        id="team_quota_test",
        organization_id="org_quota_team_test",
        name="تیم تست سهمیه",
        token_limit=80,
        used_tokens=80,  # Already exhausted!
        created_at=now,
    )
    user = UserModel(
        id="u_team_quota_user",
        email="team_quota_user@test.local",
        name="کاربر تیم سهمیه",
        password="password",
        role="user",
        organization_id="org_quota_team_test",
        team_id="team_quota_test",
        is_active=True,
        used_tokens=0,
        token_limit=50000,
        created_at=now,
    )
    db.add(org)
    db.add(team)
    db.add(user)
    db.commit()
    db.close()

    login_res = client.post("/api/auth/login", json={"email": "team_quota_user@test.local", "password": "password"})
    assert login_res.status_code == 200
    user_headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    chat_payload = {
        "message": "درخواست تحت تیم با سهمیه تمام شده",
        "conversation_id": "conv_team_quota_1",
        "language": "fa",
        "use_rag": False,
    }
    res = client.post("/api/chat", json=chat_payload, headers=user_headers)
    assert res.status_code == 200
    assert "quota_exceeded" in res.text
    assert "اتمام سهمیه توکن تیم" in res.text or "Team Quota Exceeded" in res.text


def test_org_quota_exhaustion(client):
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc).isoformat()
    
    # Create Org with tiny limit (100 tokens), team using 100 tokens
    org = OrganizationModel(
        id="org_quota_exhausted_test",
        name="سازمان بدون سهمیه",
        code="OEX",
        token_limit=100,
        created_at=now,
    )
    team = TeamModel(
        id="team_under_exhausted_org",
        organization_id="org_quota_exhausted_test",
        name="تیم ۱",
        token_limit=1000,
        used_tokens=100,  # Team used 100 which equals org limit 100
        created_at=now,
    )
    user = UserModel(
        id="u_org_quota_user",
        email="org_quota_user@test.local",
        name="کاربر سازمان",
        password="password",
        role="user",
        organization_id="org_quota_exhausted_test",
        team_id="team_under_exhausted_org",
        is_active=True,
        used_tokens=0,
        token_limit=50000,
        created_at=now,
    )
    db.add(org)
    db.add(team)
    db.add(user)
    db.commit()
    db.close()

    login_res = client.post("/api/auth/login", json={"email": "org_quota_user@test.local", "password": "password"})
    assert login_res.status_code == 200
    user_headers = {"Authorization": f"Bearer {login_res.json()['token']}"}

    chat_payload = {
        "message": "درخواست تحت سازمان با سهمیه تمام شده",
        "conversation_id": "conv_org_quota_1",
        "language": "fa",
        "use_rag": False,
    }
    res = client.post("/api/chat", json=chat_payload, headers=user_headers)
    assert res.status_code == 200
    assert "quota_exceeded" in res.text
    assert "اتمام سهمیه توکن سازمان" in res.text or "Organization Quota Exceeded" in res.text
