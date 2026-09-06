"""
Document database model for enterprise knowledge base (RAG).
"""

from typing import Any, Dict
from sqlalchemy import BigInteger, Column, Integer, String, Text

from app.db.base import Base


class DocumentModel(Base):
    __tablename__ = "sov_documents"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    size = Column(BigInteger, default=0)
    page_count = Column(Integer, default=1)
    content_type = Column(String(128), default="application/pdf")
    organization_id = Column(String(64), nullable=False, index=True)
    team_id = Column(String(64), nullable=False, index=True)
    chunk_count = Column(Integer, default=1)
    status = Column(String(32), default="indexed")
    extracted_text = Column(Text, nullable=True, default="")
    uploaded_by = Column(String(255), default="مدیر سیستم")
    created_at = Column(String(64), nullable=False)

    def to_dict(self, org_name: str = "", team_name: str = "") -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "pageCount": self.page_count,
            "contentType": self.content_type,
            "organizationId": self.organization_id,
            "organizationName": org_name,
            "teamId": self.team_id,
            "teamName": team_name,
            "chunkCount": self.chunk_count,
            "status": self.status,
            "uploadedBy": self.uploaded_by,
            "createdAt": self.created_at,
        }
