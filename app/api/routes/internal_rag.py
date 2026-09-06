"""
Internal RAG subsystem retrieval route.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from rag import rag_service

router = APIRouter(tags=["Internal RAG"])


class InternalRetrieveRequest(BaseModel):
    query: str
    top_k: int = 4
    organization_id: Optional[str] = None
    team_id: Optional[str] = None


@router.post("/rag/retrieve")
async def internal_rag_retrieve(req: InternalRetrieveRequest):
    results = rag_service.retrieve(
        query=req.query,
        organization_id=req.organization_id,
        team_id=req.team_id,
        top_k=req.top_k,
    )
    return {"results": results}
