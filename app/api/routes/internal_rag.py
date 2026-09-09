"""
Internal RAG subsystem retrieval route.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from rag import rag_service
from rag.app.http import map_to_api_error

router = APIRouter(tags=["Internal RAG"])


class InternalRetrieveRequest(BaseModel):
    query: str
    top_k: int = 4
    organization_id: Optional[str] = None
    team_id: Optional[str] = None


def verify_internal_rag_access(
    request: Request,
    db: Session = Depends(get_db),
    x_internal_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    """
    Ensures internal RAG route is accessible by authenticated users
    or internal backend services possessing the configured shared secret.
    """
    # 1. Check internal service key / bearer
    internal_token = x_internal_key
    if not internal_token and authorization and authorization.startswith("Bearer "):
        internal_token = authorization[7:].strip()

    valid_secrets = [
        s for s in [
            getattr(settings, "APP_SECRET", None),
            getattr(settings, "LITELLM_MASTER_KEY", None),
        ] if s
    ]
    if internal_token and internal_token in valid_secrets:
        return {"id": "service_internal", "role": "internal_service"}

    # 2. Check user session
    user = get_optional_user(request, db)
    if user:
        return user

    # 3. If neither provided, deny access
    raise HTTPException(
        status_code=401,
        detail="Unauthorized access to internal RAG subsystem. Valid session or internal service key required.",
    )


@router.post("/rag/retrieve")
async def internal_rag_retrieve(
    req: InternalRetrieveRequest,
    caller: Optional[Dict[str, Any]] = Depends(verify_internal_rag_access),
):
    try:
        results = rag_service.retrieve(
            query=req.query,
            organization_id=req.organization_id,
            team_id=req.team_id,
            top_k=req.top_k,
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"[InternalRAG] Retrieval failed for query '{req.query[:40]}...': {e}", exc_info=True)
        api_err = map_to_api_error(e)
        status_code = getattr(api_err, "http_status", 503)
        err_msg = getattr(api_err, "message", str(e))
        raise HTTPException(status_code=status_code, detail=f"RAG retrieval failure: {err_msg}")
