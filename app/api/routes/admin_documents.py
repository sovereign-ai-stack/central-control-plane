import asyncio
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import DeleteResponse
from app.schemas.document import DocumentListResponse
from app.services.document_service import document_service

router = APIRouter(prefix="/admin/documents", tags=["Admin Documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    organizationId: Optional[str] = None,
    teamId: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = await asyncio.to_thread(
        document_service.list_documents,
        caller=user,
        organization_id=organizationId,
        team_id=teamId,
        db=db,
    )
    return {"documents": docs}


@router.post("/upload", response_model=Dict[str, Any])
async def upload_document_admin(
    file: UploadFile = File(...),
    organizationId: Optional[str] = Form(None),
    teamId: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await document_service.upload_document(
        file=file,
        organization_id=organizationId,
        team_id=teamId,
        caller=user,
        db=db,
    )


@router.post("/text", response_model=Dict[str, Any])
async def create_text_document_admin(
    payload: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await document_service.create_text_document(
        title=payload.get("title", "سند متنی"),
        text_content=payload.get("content", ""),
        organization_id=payload.get("organizationId"),
        team_id=payload.get("teamId"),
        caller=user,
        db=db,
    )


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document_admin(
    doc_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await asyncio.to_thread(
        document_service.delete_document,
        doc_id=doc_id,
        caller=user,
        db=db,
    )
