"""
Organization API tests.
"""


def test_create_and_list_organizations(client, auth_headers):
    # 1. Create org
    create_res = client.post(
        "/api/admin/organizations",
        json={"name": "شرکت فناوری پیشرو", "code": "TECH", "tokenLimit": 5000000},
        headers=auth_headers,
    )
    assert create_res.status_code == 200
    org_data = create_res.json()
    org_id = org_data["id"]
    assert org_data["name"] == "شرکت فناوری پیشرو"
    assert org_data["code"] == "TECH"

    # 2. List orgs
    list_res = client.get("/api/admin/organizations", headers=auth_headers)
    assert list_res.status_code == 200
    orgs = list_res.json()["organizations"]
    assert any(o["id"] == org_id for o in orgs)

    # 3. Get detail
    detail_res = client.get(f"/api/admin/organizations/{org_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["organization"]["id"] == org_id

    # 4. Update org
    update_res = client.put(
        f"/api/admin/organizations/{org_id}",
        json={"name": "شرکت فناوری پیشرو نوین", "tokenLimit": 8000000},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "شرکت فناوری پیشرو نوین"

    # 5. Delete org
    delete_res = client.delete(f"/api/admin/organizations/{org_id}", headers=auth_headers)
    assert delete_res.status_code == 200
    assert delete_res.json()["deleted"] is True
