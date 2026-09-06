"""
Semantic Router Integration Client.
"""

from typing import Any, Dict, Optional

from app.core.config import settings
from app.integrations.http_client import http_call


class SemanticClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.SEMANTIC_URL

    def chat(self, query: str, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        payload = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
        }
        return http_call(f"{self.base_url}/chat", method="POST", data=payload, timeout=10)


semantic_client = SemanticClient()
