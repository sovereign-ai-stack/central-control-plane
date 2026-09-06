"""
Admin Dashboard, Models, and Limits schemas.
"""

from typing import Any, Dict, List
from pydantic import BaseModel


class ModelsListResponse(BaseModel):
    models: List[Dict[str, Any]]
