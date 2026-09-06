"""
Document schemas for RAG knowledge base.
"""

from typing import Any, Dict, List
from pydantic import BaseModel


class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
