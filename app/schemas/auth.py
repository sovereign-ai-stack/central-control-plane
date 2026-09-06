"""
Authentication schemas.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class MeResponse(BaseModel):
    user: Dict[str, Any]
