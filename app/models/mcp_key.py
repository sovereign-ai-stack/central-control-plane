"""
MCP Virtual API Key database model.
"""

from typing import Any, Dict
from sqlalchemy import Column, Integer, String

from app.db.base import Base


class McpKeyModel(Base):
    __tablename__ = "sov_mcp_keys"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    token = Column(String(128), nullable=False)
    prefix = Column(String(32), nullable=False)
    rpm = Column(Integer, default=60)
    rps = Column(Integer, default=5)
    created_at = Column(String(64), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "rpm": self.rpm,
            "rps": self.rps,
            "createdAt": self.created_at,
            "lastUsedAt": None,
            "revokedAt": None,
        }
