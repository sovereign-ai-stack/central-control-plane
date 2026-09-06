"""
Conversation database model.
"""

import json
from typing import Any, Dict
from sqlalchemy import Column, String, Text

from app.db.base import Base


class ConversationModel(Base):
    __tablename__ = "sov_conversations"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    language = Column(String(16), default="fa")
    user_id = Column(String(64), nullable=True, index=True)
    messages_json = Column(Text, default="[]")
    context_json = Column(Text, default="[]")
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        try:
            msgs = json.loads(self.messages_json or "[]")
        except Exception:
            msgs = []

        parent_conv_id = None
        parent_msg_id = None
        try:
            raw_ctx = json.loads(self.context_json or "[]")
            if isinstance(raw_ctx, dict):
                parent_conv_id = raw_ctx.get("parentConversationId")
                parent_msg_id = raw_ctx.get("parentMessageId")
                ctx_list = raw_ctx.get("facts", [])
            elif isinstance(raw_ctx, list):
                ctx_list = raw_ctx
            else:
                ctx_list = []
        except Exception:
            ctx_list = []

        return {
            "id": self.id,
            "title": self.title,
            "language": self.language,
            "userId": self.user_id,
            "status": "active",
            "messages": msgs,
            "context": ctx_list,
            "parentConversationId": parent_conv_id,
            "parentMessageId": parent_msg_id,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "expiresAt": self.updated_at,
        }
