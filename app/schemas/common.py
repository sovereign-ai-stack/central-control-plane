"""
Common schemas and base types.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
    detail: Optional[str] = None


class DeleteResponse(BaseModel):
    deleted: bool
    id: str
