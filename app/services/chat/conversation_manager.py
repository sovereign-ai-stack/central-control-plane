"""
Chat Conversation Lifecycle Manager.
Handles atomic DB operations for conversations, user prompt persistence,
message history parsing, and asynchronous token accounting.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.conversation import ConversationModel
from app.models.team import TeamModel
from app.models.user import UserModel


class ChatConversationManager:
    """Manages conversation records and token deduction transactions."""

    @staticmethod
    def prepare_conversation(
        conv_id: str,
        message: str,
        lang: str,
        user_id: Optional[str],
        user_team: Optional[str],
        db: Session,
        reply_to_id: Optional[str] = None,
        reply_to_snippet: Optional[str] = None,
    ) -> Tuple[ConversationModel, List[Dict[str, Any]], int]:
        """
        Initializes or loads conversation, appends user message, and deducts initial prompt tokens.
        """
        now = datetime.now(timezone.utc).isoformat()
        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
        if not conv:
            conv = ConversationModel(
                id=conv_id,
                title=message[:30] + ("..." if len(message) > 30 else ""),
                language=lang,
                user_id=user_id,
                messages_json="[]",
                context_json="[]",
                created_at=now,
                updated_at=now,
            )
            db.add(conv)
            db.commit()
        else:
            if conv.title in ["گفتگوی جدید", "New Conversation", ""] or not conv.messages_json or conv.messages_json == "[]":
                conv.title = message[:30] + ("..." if len(message) > 30 else "")
                db.commit()

        try:
            messages_list = json.loads(conv.messages_json or "[]")
        except Exception:
            messages_list = []

        user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        user_msg_entry = {
            "id": user_msg_id,
            "role": "user",
            "content": message,
            "createdAt": now,
        }
        if reply_to_id:
            user_msg_entry["replyToId"] = reply_to_id
        if reply_to_snippet:
            user_msg_entry["replyToSnippet"] = reply_to_snippet

        messages_list.append(user_msg_entry)
        conv.messages_json = json.dumps(messages_list, ensure_ascii=False)
        db.commit()

        # Initial prompt token deduction
        initial_token_deduct = max(5, int(len(message) / 3.5))
        if user_id:
            user_db = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user_db:
                user_db.used_tokens += initial_token_deduct
        if user_team and user_team != "global":
            team_db = db.query(TeamModel).filter(TeamModel.id == user_team).first()
            if team_db:
                team_db.used_tokens += initial_token_deduct
        db.commit()

        return conv, messages_list, initial_token_deduct

    @staticmethod
    def finalize_conversation(
        conv_id: str,
        assistant_message_obj: Dict[str, Any],
        remaining_tokens: int,
        user_id: Optional[str],
        user_team: Optional[str],
    ) -> None:
        """
        Persists assistant response and deducts remaining completion tokens in a clean DB session.
        """
        async_db = SessionLocal()
        try:
            c = async_db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
            if c:
                try:
                    cur_msgs = json.loads(c.messages_json or "[]")
                except Exception:
                    cur_msgs = []
                cur_msgs.append(assistant_message_obj)
                c.messages_json = json.dumps(cur_msgs, ensure_ascii=False)
                if c.title in ["گفتگوی جدید", "New Conversation", ""] or len(cur_msgs) <= 2:
                    first_user_msg = next((m.get("content") for m in cur_msgs if m.get("role") == "user"), None)
                    if first_user_msg:
                        c.title = first_user_msg[:30] + ("..." if len(first_user_msg) > 30 else "")
                c.updated_at = datetime.now(timezone.utc).isoformat()

            # Deduct completion tokens
            if remaining_tokens > 0:
                if user_id:
                    u_rec = async_db.query(UserModel).filter(UserModel.id == user_id).first()
                    if u_rec:
                        u_rec.used_tokens += remaining_tokens
                if user_team and user_team != "global":
                    t_rec = async_db.query(TeamModel).filter(TeamModel.id == user_team).first()
                    if t_rec:
                        t_rec.used_tokens += remaining_tokens

            async_db.commit()
        except Exception as e:
            logger.error(f"Error finalizing conversation {conv_id}: {e}")
            async_db.rollback()
        finally:
            async_db.close()
