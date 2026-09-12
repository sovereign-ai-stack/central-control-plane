"""
Admin Users API routes.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import DeleteResponse
from app.schemas.user import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    organizationId: Optional[str] = None,
    teamId: Optional[str] = None,
    roleFilter: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = user_service.list_users(
        caller=user,
        organization_id=organizationId,
        team_id=teamId,
        role_filter=roleFilter,
        db=db,
    )
    return {"users": users}


@router.post("", response_model=Dict[str, Any])
async def create_user(payload: CreateUserRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.create_user(payload=payload, caller=user, db=db)


@router.put("/{user_id}", response_model=Dict[str, Any])
async def update_user(user_id: str, payload: UpdateUserRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.update_user(user_id=user_id, payload=payload, caller=user, db=db)


@router.delete("/{user_id}", response_model=DeleteResponse)
async def delete_user(user_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.delete_user(user_id=user_id, caller=user, db=db)


@router.post("/sync-litellm", response_model=Dict[str, Any])
async def reconcile_litellm_users(user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.reconcile_all_users_with_litellm(caller=user, db=db)


@router.post("/{user_id}/sync-litellm", response_model=Dict[str, Any])
async def sync_litellm_user(user_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.sync_user_by_id(user_id=user_id, caller=user, db=db)
