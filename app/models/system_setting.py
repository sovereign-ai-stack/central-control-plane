"""
System Settings database model for dynamic cluster & reasoning configuration.
"""

from typing import Any, Dict
from sqlalchemy import Column, String

from app.db.base import Base


class SystemSettingModel(Base):
    __tablename__ = "sov_system_settings"

    key = Column(String(64), primary_key=True, index=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(String(64), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "updatedAt": self.updated_at,
        }
