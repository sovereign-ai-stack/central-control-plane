"""
Chat streaming API route.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.chat import SendMessageRequest
from app.services.chat_service import chat_service

router = APIRouter(tags=["Chat"])


@router.post("/chat")
async def chat_stream(
    payload: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_service.process_chat_stream(payload=payload, user=user, db=db)
