"""
Conversation schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CreateConversationRequest(BaseModel):
    language: Optional[str] = "fa"
    title: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    language: Optional[str] = None


class ConversationListResponse(BaseModel):
    conversations: List[Dict[str, Any]]


class ShareConversationResponse(BaseModel):
    token: str
    conversationId: str


class BranchConversationRequest(BaseModel):
    sourceMessageId: Optional[str] = None
    mode: Optional[str] = "branch"

