"""
User API tests.
"""


def test_create_and_manage_users(client, auth_headers):
    # 1. Create a user
    create_res = client.post(
        "/api/admin/users",
        json={
            "email": "sarah@sovereign.local",
            "name": "سارا محمدی",
            "password": "password123",
            "role": "org_admin",
            "tokenLimit": 1000000,
        },
        headers=auth_headers,
    )
    assert create_res.status_code == 200
    user_data = create_res.json()
    user_id = user_data["id"]
    assert user_data["email"] == "sarah@sovereign.local"
    assert user_data["role"] == "org_admin"

    # 2. List users
    list_res = client.get("/api/admin/users", headers=auth_headers)
    assert list_res.status_code == 200
    users = list_res.json()["users"]
    assert any(u["id"] == user_id for u in users)

    # 3. Update user
    update_res = client.put(
        f"/api/admin/users/{user_id}",
        json={"name": "سارا محمدی اصل", "isActive": False},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "سارا محمدی اصل"
    assert update_res.json()["isActive"] is False

    # 4. Delete user
    delete_res = client.delete(f"/api/admin/users/{user_id}", headers=auth_headers)
    assert delete_res.status_code == 200
    assert delete_res.json()["deleted"] is True
