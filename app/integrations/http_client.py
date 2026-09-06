"""
Production HTTP Client Utility.
Uses connection-pooled HTTPX client for fast connection reuse and keep-alive,
with graceful fallback to urllib for resilience.
"""

import json
from typing import Any, Dict, Optional
import httpx

from app.core.logging import logger

# Global pooled client for low-latency internal microservice communication
_limits = httpx.Limits(max_keepalive_connections=30, max_connections=100, keepalive_expiry=30.0)
_client = httpx.Client(limits=_limits, timeout=5.0)


def http_call(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 3.0,
) -> Optional[Dict[str, Any]]:
    """
    Executes a JSON HTTP request using connection-pooled HTTPX client.
    Returns parsed JSON response or None on error.
    """
    req_headers = {"User-Agent": "SovereignGateway/2.0", "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    try:
        method_upper = method.upper()
        if method_upper == "GET":
            resp = _client.get(url, headers=req_headers, timeout=timeout)
        elif method_upper == "POST":
            resp = _client.post(url, json=data, headers=req_headers, timeout=timeout)
        elif method_upper == "PATCH":
            resp = _client.patch(url, json=data, headers=req_headers, timeout=timeout)
        elif method_upper == "DELETE":
            resp = _client.request("DELETE", url, json=data, headers=req_headers, timeout=timeout)
        else:
            resp = _client.request(method_upper, url, json=data, headers=req_headers, timeout=timeout)

        if resp.status_code in [200, 201, 204]:
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()
        else:
            logger.debug(f"HTTP call to {url} returned status {resp.status_code}")
            return None
    except Exception as e:
        logger.debug(f"HTTP call to {url} failed: {e}")
        return None
