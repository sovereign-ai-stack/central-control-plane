"""
Conversation business logic service.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.conversation import ConversationModel
from app.schemas.conversation import (
    CreateConversationRequest,
    UpdateConversationRequest,
    BranchConversationRequest,
)


class ConversationService:
    @staticmethod
    def list_conversations(user: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        convs = db.query(ConversationModel).filter(
            ConversationModel.user_id == user.get("id")
        ).order_by(ConversationModel.updated_at.desc()).all()
        return [c.to_dict() for c in convs]

    @staticmethod
    def create_conversation(payload: Optional[CreateConversationRequest], user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        user_id = user.get("id")
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        lang = (payload.language if payload and payload.language else "fa")
        title = (payload.title if payload and payload.title else ("گفتگوی جدید" if lang == "fa" else "New Conversation"))

        new_conv = ConversationModel(
            id=conv_id,
            title=title,
            language=lang,
            user_id=user_id,
            messages_json="[]",
            context_json="[]",
            created_at=now,
            updated_at=now,
        )
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return new_conv.to_dict()

    @staticmethod
    def get_conversation(conv_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="گفتگو یافت نشد.")
        return conv.to_dict()

    @staticmethod
    def update_conversation(conv_id: str, payload: UpdateConversationRequest, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="گفتگو یافت نشد.")
        if payload.title is not None:
            conv.title = payload.title
        if payload.language is not None:
            conv.language = payload.language
        conv.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(conv)
        return conv.to_dict()

    @staticmethod
    def delete_conversation(conv_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if conv:
            db.delete(conv)
            db.commit()
        return {"deleted": True, "id": conv_id}

    @staticmethod
    def share_conversation(conv_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="گفتگو یافت نشد.")
        token = f"share_{uuid.uuid4().hex[:16]}"
        return {"token": token, "conversationId": conv_id}

    @staticmethod
    def branch_conversation(
        conv_id: str,
        payload: Optional[BranchConversationRequest],
        user: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="گفتگو یافت نشد.")

        try:
            msgs = json.loads(conv.messages_json or "[]")
        except Exception:
            msgs = []

        source_msg_id = payload.sourceMessageId if payload else None
        branched_msgs = list(msgs)
        if source_msg_id:
            target_idx = -1
            for i, m in enumerate(msgs):
                if m.get("id") == source_msg_id:
                    target_idx = i
                    break
            if target_idx != -1:
                # Include all messages up to and including the targeted message
                branched_msgs = msgs[:target_idx + 1]

        # Create a brand new conversation as a branch
        new_conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        branch_suffix = " (شاخه)" if conv.language == "fa" else " (Branch)"
        base_title = conv.title.replace(" (شاخه)", "").replace(" (Branch)", "")
        # Store branch lineage metadata
        branch_meta = {
            "parentConversationId": conv_id,
            "parentMessageId": source_msg_id,
        }

        new_conv = ConversationModel(
            id=new_conv_id,
            title=new_title,
            language=conv.language,
            user_id=user.get("id"),
            messages_json=json.dumps(branched_msgs, ensure_ascii=False),
            context_json=json.dumps(branch_meta, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return new_conv.to_dict()

    @staticmethod
    def edit_conversation(
        conv_id: str,
        payload: Optional[BranchConversationRequest],
        user: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="گفتگو یافت نشد.")

        try:
            msgs = json.loads(conv.messages_json or "[]")
        except Exception:
            msgs = []

        source_msg_id = payload.sourceMessageId if payload else None
        if source_msg_id:
            target_idx = -1
            for i, m in enumerate(msgs):
                if m.get("id") == source_msg_id:
                    target_idx = i
                    break
            if target_idx != -1:
                # Truncate messages before the edited user message
                conv.messages_json = json.dumps(msgs[:target_idx], ensure_ascii=False)
                conv.updated_at = datetime.now(timezone.utc).isoformat()
                db.commit()
                db.refresh(conv)

        return conv.to_dict()


conversation_service = ConversationService()
