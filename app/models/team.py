"""
Team database model.
"""

from typing import Any, Dict
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class TeamModel(Base):
    __tablename__ = "sov_teams"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("sov_organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    litellm_team_id = Column(String(128), index=True)
    name = Column(String(255), nullable=False)
    token_limit = Column(BigInteger, default=2000000)
    used_tokens = Column(BigInteger, default=0)
    rpm_limit = Column(Integer, default=100)
    tpm_limit = Column(Integer, default=100000)
    created_at = Column(String(64), nullable=False)

    organization = relationship("OrganizationModel", back_populates="teams")
    users = relationship("UserModel", back_populates="team")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organizationId": self.organization_id,
            "organizationName": self.organization.name if self.organization else "",
            "litellmTeamId": self.litellm_team_id or f"{self.organization_id}:{self.id}",
            "name": self.name,
            "tokenLimit": self.token_limit,
            "usedTokens": self.used_tokens,
            "memberCount": len(self.users) if self.users is not None else 0,
            "rpmLimit": self.rpm_limit,
            "tpmLimit": self.tpm_limit,
            "createdAt": self.created_at,
        }
