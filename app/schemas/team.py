"""
Team schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CreateTeamRequest(BaseModel):
    name: str
    organizationId: str
    tokenLimit: Optional[int] = 2000000
    rpmLimit: Optional[int] = 100
    tpmLimit: Optional[int] = 100000


class UpdateTeamRequest(BaseModel):
    name: Optional[str] = None
    tokenLimit: Optional[int] = None
    rpmLimit: Optional[int] = None
    tpmLimit: Optional[int] = None


class TeamListResponse(BaseModel):
    teams: List[Dict[str, Any]]


class TeamDetailResponse(BaseModel):
    team: Dict[str, Any]
    members: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
