"""
Admin Organizations API routes.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import DeleteResponse
from app.schemas.organization import (
    CreateOrgRequest,
    UpdateOrgRequest,
    OrganizationListResponse,
    OrganizationDetailResponse,
)
from app.services.organization_service import organization_service

router = APIRouter(prefix="/admin/organizations", tags=["Admin Organizations"])


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    orgs = organization_service.list_organizations(user=user, db=db)
    return {"organizations": orgs}


@router.get("/{org_id}", response_model=OrganizationDetailResponse)
async def get_organization_detail(org_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return organization_service.get_organization_detail(org_id=org_id, user=user, db=db)


@router.post("", response_model=Dict[str, Any])
async def create_organization(payload: CreateOrgRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return organization_service.create_organization(payload=payload, user=user, db=db)


@router.put("/{org_id}", response_model=Dict[str, Any])
async def update_organization(org_id: str, payload: UpdateOrgRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return organization_service.update_organization(org_id=org_id, payload=payload, user=user, db=db)


@router.delete("/{org_id}", response_model=DeleteResponse)
async def delete_organization(org_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return organization_service.delete_organization(org_id=org_id, user=user, db=db)
