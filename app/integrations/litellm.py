"""
LiteLLM Proxy Integration Client.
Handles syncing virtual teams, users, budgets, keys, and chat completions.
"""

import json
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.integrations.http_client import http_call


class LiteLLMClient:
    def __init__(self, base_url: Optional[str] = None, master_key: Optional[str] = None):
        self.base_url = base_url or settings.LITELLM_URL
        self.master_key = master_key or settings.LITELLM_MASTER_KEY

    @property
    def auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.master_key}"}

    def sync_team(
        self,
        litellm_team_id: str,
        team_alias: str,
        max_budget: float,
        rpm_limit: int,
        tpm_limit: int,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/team/new"
        payload = {
            "team_id": litellm_team_id,
            "team_alias": team_alias,
            "max_budget": max_budget,
            "budget_duration": "30d",
            "rpm_limit": rpm_limit,
            "tpm_limit": tpm_limit,
            "metadata": {"organizationId": org_id, "source": "sovereign-control-plane"},
        }
        return http_call(url, method="POST", data=payload, headers=self.auth_headers, timeout=3)

    def update_team(
        self,
        litellm_team_id: str,
        team_alias: str,
        max_budget: float,
        rpm_limit: int,
        tpm_limit: int,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/team/update"
        payload = {
            "team_id": litellm_team_id,
            "team_alias": team_alias,
            "max_budget": max_budget,
            "rpm_limit": rpm_limit,
            "tpm_limit": tpm_limit,
        }
        return http_call(url, method="POST", data=payload, headers=self.auth_headers, timeout=3)

    def delete_teams(self, team_ids: List[str]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/team/delete"
        return http_call(url, method="POST", data={"team_ids": team_ids}, headers=self.auth_headers, timeout=3)

    def sync_user(
        self,
        user_id: str,
        email: str,
        litellm_team_id: Optional[str],
        token_limit: int,
        role: str,
    ):
        try:
            user_role = "proxy_admin" if role == "super_admin" else "internal_user"
            budget_float = float(token_limit)

            # 1. Set individual user budget in LiteLLM User Table
            payload = {
                "user_id": user_id,
                "user_email": email,
                "user_role": user_role,
                "max_budget": budget_float,
                "teams": [litellm_team_id] if litellm_team_id else [],
            }
            res = http_call(f"{self.base_url}/user/new", method="POST", data=payload, headers=self.auth_headers, timeout=3)
            if not res:
                http_call(f"{self.base_url}/user/update", method="POST", data=payload, headers=self.auth_headers, timeout=3)

            # 2. Update all Virtual Keys belonging to this user
            user_info = http_call(f"{self.base_url}/user/info?user_id={user_id}", method="GET", headers=self.auth_headers, timeout=3)
            if user_info and "keys" in user_info:
                for k in user_info.get("keys", []):
                    k_token = k.get("token")
                    if k_token:
                        http_call(
                            f"{self.base_url}/key/update",
                            method="POST",
                            data={"key": k_token, "max_budget": budget_float},
                            headers=self.auth_headers,
                            timeout=3,
                        )

            # 3. Add / sync user to LiteLLM Team
            if litellm_team_id:
                member_role = "admin" if role in ["super_admin", "org_admin", "team_admin"] else "user"
                member_payload = {
                    "team_id": litellm_team_id,
                    "member": {
                        "role": member_role,
                        "user_id": user_id,
                        "user_email": email,
                    },
                }
                http_call(f"{self.base_url}/team/member_add", method="POST", data=member_payload, headers=self.auth_headers, timeout=3)

            logger.info(f"Synchronized user {user_id} ({email}) with LiteLLM (Team: {litellm_team_id}, User Budget: {token_limit})")
        except Exception as e:
            logger.warning(f"Failed to sync user {user_id} with LiteLLM: {e}")

    def delete_user(self, user_id: str, litellm_team_id: Optional[str] = None):
        try:
            http_call(f"{self.base_url}/user/delete", method="POST", data={"user_ids": [user_id]}, headers=self.auth_headers, timeout=3)
            if litellm_team_id:
                http_call(f"{self.base_url}/team/member_delete", method="POST", data={"team_id": litellm_team_id, "user_id": user_id}, headers=self.auth_headers, timeout=3)
            logger.info(f"Deleted user {user_id} from LiteLLM")
        except Exception as e:
            logger.warning(f"Failed to delete user {user_id} from LiteLLM: {e}")

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "model": model,
            "messages": messages,
            "user": user_id,
        }
        if metadata:
            payload["metadata"] = metadata
        return http_call(
            f"{self.base_url}/chat/completions",
            method="POST",
            data=payload,
            headers=self.auth_headers,
            timeout=60.0,
        )

    async def chat_completion_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: float = 120.0,
    ):
        """Streams chat completion chunks from LiteLLM / local inference engine via SSE."""
        import httpx
        payload = {
            "model": model,
            "messages": messages,
            "user": user_id,
            "stream": True,
        }
        if metadata:
            payload["metadata"] = metadata

        url = f"{self.base_url}/chat/completions"
        headers = {"User-Agent": "SovereignGateway/2.0", "Content-Type": "application/json"}
        headers.update(self.auth_headers)

        client = httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=15.0, read=timeout, write=15.0))
        try:
            req = client.build_request("POST", url, json=payload, headers=headers)
            response = await client.send(req, stream=True)
            if response.status_code != 200:
                err_bytes = await response.aread()
                logger.warning(
                    f"LiteLLM stream call to {url} failed with status {response.status_code}: {err_bytes.decode('utf-8', errors='ignore')}"
                )
                await response.aclose()
                return

            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    yield chunk
                except Exception:
                    continue
            await response.aclose()
        except Exception as e:
            logger.debug(f"LiteLLM stream exception: {e}")
        finally:
            await client.aclose()

    def get_registered_models(self) -> List[Dict[str, Any]]:
        """Fetches all registered models in LiteLLM Proxy via /model/info."""
        try:
            res = http_call(f"{self.base_url}/model/info", method="GET", headers=self.auth_headers, timeout=5)
            if res and isinstance(res, dict) and "data" in res:
                return res["data"]
            return []
        except Exception as e:
            logger.warning(f"Error fetching models from LiteLLM proxy: {e}")
            return []

    def delete_model_by_id(self, model_id: str) -> bool:
        """Deletes a model from LiteLLM Proxy by its internal ID."""
        try:
            res = http_call(f"{self.base_url}/model/delete", method="POST", data={"id": model_id}, headers=self.auth_headers, timeout=5)
            return bool(res)
        except Exception as e:
            logger.warning(f"Error deleting model {model_id} from LiteLLM proxy: {e}")
            return False

    def register_model(
        self,
        model_name: str,
        litellm_model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        payload = {
            "model_name": model_name,
            "litellm_params": {
                "model": litellm_model,
                "drop_params": True,
            },
            "model_info": model_info or {"mode": "chat"},
        }
        if api_key:
            payload["litellm_params"]["api_key"] = api_key
        if api_base:
            payload["litellm_params"]["api_base"] = api_base

        res = http_call(f"{self.base_url}/model/new", method="POST", data=payload, headers=self.auth_headers, timeout=5)
        if not res:
            res = http_call(f"{self.base_url}/model/update", method="POST", data=payload, headers=self.auth_headers, timeout=5)
        return bool(res)

    def delete_model_from_proxy(self, model_name: str, model_id: Optional[str] = None) -> bool:
        try:
            payload = {"id": model_id} if model_id else {"model_name": model_name}
            res = http_call(f"{self.base_url}/model/delete", method="POST", data=payload, headers=self.auth_headers, timeout=5)
            return bool(res)
        except Exception as e:
            logger.warning(f"Error deleting model from LiteLLM proxy: {e}")
            return False

    def health_check(self) -> Optional[Dict[str, Any]]:
        return http_call(f"{self.base_url}/health", timeout=1)


litellm_client = LiteLLMClient()

