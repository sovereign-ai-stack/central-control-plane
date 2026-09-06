"""
Admin Dashboard, Overview, Models, and Limits API routes.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user
from app.db.session import get_db
from app.schemas.dashboard import ModelsListResponse
from app.services.dashboard_service import dashboard_service

router = APIRouter(tags=["Admin Dashboard"])


@router.get("/admin/dashboard", response_model=Dict[str, Any])
@router.get("/admin/overview", response_model=Dict[str, Any])
async def get_admin_dashboard(user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard_service.get_dashboard(user=user, db=db)


@router.get("/admin/limits", response_model=Dict[str, Any])
@router.get("/usage-limits", response_model=Dict[str, Any])
async def get_admin_limits(user: Optional[Dict[str, Any]] = Depends(get_optional_user), db: Session = Depends(get_db)):
    return dashboard_service.get_limits(user=user, db=db)
