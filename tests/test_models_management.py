import pytest


def test_managed_models_crud(client, auth_headers):
    # 1. List models
    res = client.get("/api/admin/models", headers=auth_headers)
    assert res.status_code == 200
    assert "models" in res.json()

    # 2. Add Gemini Model
    gemini_payload = {
        "name": "Gemini 1.5 Pro Test",
        "provider": "gemini",
        "modelId": "gemini-1.5-pro",
        "assignedRole": "general-model",
        "apiKey": "AIzaSyTestGeminiKey1234567890",
        "contextWindow": 1000000,
        "isEnabled": True,
    }
    res_add = client.post("/api/admin/models", json=gemini_payload, headers=auth_headers)
    assert res_add.status_code == 200
    gemini_model = res_add.json()
    assert gemini_model["name"] == "Gemini 1.5 Pro Test"
    assert gemini_model["provider"] == "gemini"
    assert gemini_model["hasKey"] is True
    assert gemini_model["apiKey"].startswith("AIzaSyT...")  # Key is securely masked!
    model_id = gemini_model["id"]

    # 3. Add DeepSeek Model
    deepseek_payload = {
        "name": "DeepSeek R1 Test",
        "provider": "deepseek",
        "modelId": "deepseek-reasoner",
        "assignedRole": "reasoning-model",
        "apiKey": "sk-deepseek-test-key-9999",
        "apiBase": "https://api.deepseek.com",
        "contextWindow": 64000,
        "isEnabled": True,
    }
    res_ds = client.post("/api/admin/models", json=deepseek_payload, headers=auth_headers)
    assert res_ds.status_code == 200
    ds_model = res_ds.json()
    assert ds_model["provider"] == "deepseek"
    assert ds_model["assignedRole"] == "reasoning-model"

    # 4. Toggle Model state
    res_toggle = client.patch(f"/api/admin/models/{model_id}/toggle", json={"isEnabled": False}, headers=auth_headers)
    assert res_toggle.status_code == 200
    assert res_toggle.json()["isEnabled"] is False

    # 5. Delete Model
    res_del = client.delete(f"/api/admin/models/{model_id}", headers=auth_headers)
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True
