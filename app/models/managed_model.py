"""
Managed Model database model for dynamic AI Model and Node orchestration.
"""

from typing import Any, Dict
from sqlalchemy import Boolean, Column, Integer, String

from app.db.base import Base


class ManagedModelModel(Base):
    __tablename__ = "sov_managed_models"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    provider = Column(String(64), nullable=False, default="openai")
    model_id = Column(String(255), nullable=False)
    api_key = Column(String(512), nullable=True, default="")
    api_base = Column(String(512), nullable=True, default="")
    assigned_role = Column(String(64), nullable=False, default="general-model")
    is_enabled = Column(Boolean, default=True)
    context_window = Column(Integer, default=32768)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)

    def to_dict(self, mask_key: bool = True) -> Dict[str, Any]:
        raw_key = self.api_key or ""
        if mask_key and raw_key:
            masked_key = raw_key[:7] + "..." + raw_key[-4:] if len(raw_key) > 12 else "sk-..."
        else:
            masked_key = raw_key

        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "modelId": self.model_id,
            "apiKey": masked_key,
            "hasKey": bool(raw_key),
            "apiBase": self.api_base or "",
            "assignedRole": self.assigned_role,
            "isEnabled": bool(self.is_enabled),
            "contextWindow": self.context_window or 32768,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
