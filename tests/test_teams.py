"""
Team API tests.
"""


def test_create_and_manage_teams(client, auth_headers):
    # 1. First create an organization for team
    org_res = client.post(
        "/api/admin/organizations",
        json={"name": "سازمان مرکزی", "code": "CEN"},
        headers=auth_headers,
    )
    assert org_res.status_code == 200
    org_id = org_res.json()["id"]

    # 2. Create team
    create_res = client.post(
        "/api/admin/teams",
        json={"name": "تیم توسعه هوش مصنوعی", "organizationId": org_id, "tokenLimit": 3000000},
        headers=auth_headers,
    )
    assert create_res.status_code == 200
    team_data = create_res.json()
    team_id = team_data["id"]
    assert team_data["name"] == "تیم توسعه هوش مصنوعی"
    assert team_data["organizationId"] == org_id

    # 3. List teams
    list_res = client.get("/api/admin/teams", headers=auth_headers)
    assert list_res.status_code == 200
    teams = list_res.json()["teams"]
    assert any(t["id"] == team_id for t in teams)

    # 4. Get team detail
    detail_res = client.get(f"/api/admin/teams/{team_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["team"]["id"] == team_id

    # 5. Update team
    update_res = client.put(
        f"/api/admin/teams/{team_id}",
        json={"name": "تیم تحقیق و توسعه هوش مصنوعی", "tokenLimit": 4000000},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "تیم تحقیق و توسعه هوش مصنوعی"

    # 6. Delete team
    delete_res = client.delete(f"/api/admin/teams/{team_id}", headers=auth_headers)
    assert delete_res.status_code == 200
    assert delete_res.json()["deleted"] is True
