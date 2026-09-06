"""
Organization schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CreateOrgRequest(BaseModel):
    name: str
    code: Optional[str] = None
    tokenLimit: Optional[int] = 10000000


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    tokenLimit: Optional[int] = None


class OrganizationListResponse(BaseModel):
    organizations: List[Dict[str, Any]]


class OrganizationDetailResponse(BaseModel):
    organization: Dict[str, Any]
    teams: List[Dict[str, Any]]
    users: List[Dict[str, Any]]
