"""
Conversations API routes.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import DeleteResponse
from app.schemas.conversation import (
    CreateConversationRequest,
    UpdateConversationRequest,
    ConversationListResponse,
    ShareConversationResponse,
    BranchConversationRequest,
)
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = conversation_service.list_conversations(user=user, db=db)
    return {"conversations": convs}


@router.post("", response_model=Dict[str, Any])
async def create_conversation(
    payload: Optional[CreateConversationRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return conversation_service.create_conversation(payload=payload, user=user, db=db)


@router.get("/{conv_id}", response_model=Dict[str, Any])
async def get_conversation(conv_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return conversation_service.get_conversation(conv_id=conv_id, user=user, db=db)


@router.patch("/{conv_id}", response_model=Dict[str, Any])
async def update_conversation(
    conv_id: str,
    payload: UpdateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return conversation_service.update_conversation(conv_id=conv_id, payload=payload, user=user, db=db)


@router.delete("/{conv_id}", response_model=DeleteResponse)
async def delete_conversation(conv_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return conversation_service.delete_conversation(conv_id=conv_id, user=user, db=db)


@router.post("/{conv_id}/share", response_model=ShareConversationResponse)
async def share_conversation(conv_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return conversation_service.share_conversation(conv_id=conv_id, user=user, db=db)


@router.post("/{conv_id}/branch", response_model=Dict[str, Any])
async def branch_conversation(
    conv_id: str,
    payload: Optional[BranchConversationRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return conversation_service.branch_conversation(conv_id=conv_id, payload=payload, user=user, db=db)


@router.post("/{conv_id}/edit", response_model=Dict[str, Any])
async def edit_conversation(
    conv_id: str,
    payload: Optional[BranchConversationRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return conversation_service.edit_conversation(conv_id=conv_id, payload=payload, user=user, db=db)
