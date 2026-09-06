"""
Organization database model.
"""

from typing import Any, Dict
from sqlalchemy import BigInteger, Column, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class OrganizationModel(Base):
    __tablename__ = "sov_organizations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(32), nullable=True)
    token_limit = Column(BigInteger, default=10000000)
    created_at = Column(String(64), nullable=False)

    teams = relationship("TeamModel", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("UserModel", back_populates="organization")

    def to_dict(self, total_used_tokens: int = 0) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code or self.name[:3].upper(),
            "tokenLimit": self.token_limit,
            "usedTokens": total_used_tokens,
            "teamCount": len(self.teams) if self.teams is not None else 0,
            "userCount": len(self.users) if self.users is not None else 0,
            "createdAt": self.created_at,
        }
