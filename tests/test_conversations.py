"""
Conversations and Limits API tests.
"""


def test_conversations_crud(client, auth_headers):
    # 1. Create conversation
    create_res = client.post(
        "/api/conversations",
        json={"title": "تحلیل معماری سیستم", "language": "fa"},
        headers=auth_headers,
    )
    assert create_res.status_code == 200
    conv_data = create_res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "تحلیل معماری سیستم"

    # 2. List conversations
    list_res = client.get("/api/conversations", headers=auth_headers)
    assert list_res.status_code == 200
    convs = list_res.json()["conversations"]
    assert any(c["id"] == conv_id for c in convs)

    # 3. Get single conversation
    get_res = client.get(f"/api/conversations/{conv_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == conv_id

    # 4. Update conversation
    update_res = client.patch(
        f"/api/conversations/{conv_id}",
        json={"title": "تحلیل معماری سازمانی نوین"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "تحلیل معماری سازمانی نوین"

    # 5. Share conversation
    share_res = client.post(f"/api/conversations/{conv_id}/share", headers=auth_headers)
    assert share_res.status_code == 200
    assert "token" in share_res.json()

    # 6. Delete conversation
    delete_res = client.delete(f"/api/conversations/{conv_id}", headers=auth_headers)
    assert delete_res.status_code == 200
    assert delete_res.json()["deleted"] is True


def test_limits_and_dashboard(client, auth_headers):
    # Dashboard
    dash_res = client.get("/api/admin/dashboard", headers=auth_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "totalUsers" in dash_data
    assert "tokenUsagePercent" in dash_data

    # Limits
    limits_res = client.get("/api/admin/limits", headers=auth_headers)
    assert limits_res.status_code == 200
    limits_data = limits_res.json()
    assert "maxConversations" in limits_data
    assert "totalTokenLimit" in limits_data
