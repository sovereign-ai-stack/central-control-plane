"""
Production Health & Readiness Check API routes.
Provides liveness probe (/health) and readiness probe (/health/ready)
with live database connectivity verification and dependency diagnostics.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.integrations.litellm import litellm_client
from app.integrations.registry import registry_client

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Lightweight liveness probe for container orchestrators (Kubernetes / Docker)."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@router.get("/health/ready", response_model=Dict[str, Any])
async def readiness_check(db: Session = Depends(get_db)):
    """
    Deep readiness probe verifying persistent database connectivity
    and status of peripheral cluster subsystems.
    """
    # 1. Verify Database Connectivity
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(e)}",
        )

    # 2. Check LiteLLM Proxy Status
    litellm_status = "unreachable"
    try:
        res = litellm_client.health_check()
        if res:
            litellm_status = "healthy"
    except Exception:
        pass

    # 3. Check Node Registry Status
    registry_status = "unreachable"
    node_count = 0
    try:
        nodes = registry_client.get_nodes()
        registry_status = "healthy"
        node_count = len(nodes)
    except Exception:
        pass

    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": {
            "database": "connected" if db_ok else "failed",
            "litellm_proxy": litellm_status,
            "node_registry": registry_status,
            "active_gpu_nodes": node_count,
        },
    }
