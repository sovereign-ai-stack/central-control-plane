"""
User and Session database models.
"""

from typing import Any, Dict
from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserModel(Base):
    __tablename__ = "sov_users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="user")  # super_admin, org_admin, team_admin, user
    organization_id = Column(String(64), ForeignKey("sov_organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(String(64), ForeignKey("sov_teams.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    litellm_synced = Column(Boolean, default=False)
    litellm_sync_error = Column(String(500), nullable=True)
    used_tokens = Column(BigInteger, default=0)
    token_limit = Column(BigInteger, default=500000)
    created_at = Column(String(64), nullable=False)

    organization = relationship("OrganizationModel", back_populates="users")
    team = relationship("TeamModel", back_populates="users")

    def to_dict(self) -> Dict[str, Any]:
        used_pct = min(100, int((self.used_tokens / max(1, self.token_limit)) * 100))
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "organizationId": self.organization_id,
            "organizationName": self.organization.name if self.organization else "",
            "teamId": self.team_id,
            "teamName": self.team.name if self.team else "",
            "isActive": self.is_active,
            "litellmSynced": bool(self.litellm_synced),
            "litellmSyncError": self.litellm_sync_error,
            "usedTokens": self.used_tokens,
            "tokenLimit": self.token_limit,
            "usedPercent": used_pct,
            "status": "healthy" if self.is_active else "disabled",
            "createdAt": self.created_at,
        }


class SessionModel(Base):
    __tablename__ = "sov_sessions"

    token = Column(String(128), primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    created_at = Column(String(64), nullable=False)
