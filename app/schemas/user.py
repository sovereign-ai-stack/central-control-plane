"""
User schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str
    role: str
    organizationId: Optional[str] = None
    teamId: Optional[str] = None
    tokenLimit: Optional[int] = 500000


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    organizationId: Optional[str] = None
    teamId: Optional[str] = None
    tokenLimit: Optional[int] = None
    isActive: Optional[bool] = None


class UserListResponse(BaseModel):
    users: List[Dict[str, Any]]
