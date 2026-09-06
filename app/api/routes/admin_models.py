"""
Admin Dynamic Model and AI Node Orchestration API routes.
Restricted exclusively to super_admin.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.managed_model import (
    CreateModelRequest,
    ManagedModelsListResponse,
    ToggleModelRequest,
)
from app.services.managed_model_service import managed_model_service

router = APIRouter(tags=["Admin Models Orchestration"])


def _require_super_admin(user: Dict[str, Any]) -> None:
    role = user.get("role")
    if role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="دسترسی غیرمجاز: تنها مدیر کل سامانه (super_admin) مجاز به پیکربندی مدل‌ها و نودهای پردازشی است."
        )


@router.get("/admin/models", response_model=ManagedModelsListResponse)
async def get_managed_models(
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_super_admin(user)
    return managed_model_service.list_all(db=db)


@router.post("/admin/models", response_model=Dict[str, Any])
async def create_managed_model(
    payload: CreateModelRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_super_admin(user)
    
    model_id = payload.model_id or payload.modelId
    if not model_id:
        raise HTTPException(status_code=400, detail="شناسه مدل (model_id) الزامی است.")

    assigned_role = payload.assigned_role or payload.assignedRole or "general-model"
    api_key = payload.api_key or payload.apiKey or ""
    api_base = payload.api_base or payload.apiBase or ""
    context_window = payload.context_window if payload.context_window is not None else (payload.contextWindow or 32768)
    is_enabled = payload.is_enabled if payload.is_enabled is not None else (payload.isEnabled if payload.isEnabled is not None else True)

    try:
        new_model = managed_model_service.create_model(
            name=payload.name,
            provider=payload.provider,
            model_id=model_id,
            assigned_role=assigned_role,
            api_key=api_key,
            api_base=api_base,
            context_window=context_window,
            is_enabled=is_enabled,
            db=db,
        )
        return new_model
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خطا در افزودن مدل: {str(e)}")


@router.patch("/admin/models/{model_id}/toggle", response_model=Dict[str, Any])
async def toggle_managed_model(
    model_id: str,
    payload: ToggleModelRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_super_admin(user)
    target_state = payload.is_enabled if payload.is_enabled is not None else payload.isEnabled
    try:
        updated = managed_model_service.toggle_model(model_id=model_id, is_enabled=target_state, db=db)
        return updated
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"خطا در تغییر وضعیت مدل: {str(e)}")


@router.delete("/admin/models/{model_id}", response_model=Dict[str, Any])
async def delete_managed_model(
    model_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_super_admin(user)
    try:
        return managed_model_service.delete_model(model_id=model_id, db=db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خطا در حذف مدل: {str(e)}")


@router.post("/admin/models/{model_id}/test", response_model=Dict[str, Any])
async def test_managed_model(
    model_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sends a live test inference request to verify model health and measure latency."""
    _require_super_admin(user)
    try:
        return managed_model_service.test_model(model_id=model_id, db=db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خطا در تست اتصال مدل: {str(e)}")

