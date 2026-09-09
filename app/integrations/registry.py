"""
Central Node Registry Integration Client.
"""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.integrations.http_client import http_call


class RegistryClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.REGISTRY_URL

    def get_nodes(self) -> List[Dict[str, Any]]:
        registry_data = http_call(f"{self.base_url}/nodes", timeout=2)
        if isinstance(registry_data, list):
            return registry_data
        elif isinstance(registry_data, dict):
            return registry_data.get("nodes", [])
        return []


registry_client = RegistryClient()
