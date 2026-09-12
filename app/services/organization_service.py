"""
Organization business logic service.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.integrations.litellm import litellm_client
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.models.user import UserModel
from app.schemas.organization import CreateOrgRequest, UpdateOrgRequest


class OrganizationService:
    @staticmethod
    def get_organization_used_tokens(db: Session, org_id: str) -> int:
        """
        Canonical single source of truth for organization token consumption.
        Computes the sum of used tokens across all users belonging to the organization.
        """
        return (
            db.query(func.coalesce(func.sum(UserModel.used_tokens), 0))
            .filter(UserModel.organization_id == org_id)
            .scalar()
            or 0
        )

    @staticmethod
    def list_organizations(user: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        role = user.get("role", "super_admin")
        user_org_id = user.get("organizationId")

        if role == "super_admin":
            orgs = db.query(OrganizationModel).all()
        elif user_org_id:
            orgs = db.query(OrganizationModel).filter(OrganizationModel.id == user_org_id).all()
        else:
            orgs = []

        res = []
        for org in orgs:
            used_tokens = OrganizationService.get_organization_used_tokens(db, org.id)
            res.append(org.to_dict(total_used_tokens=used_tokens))
        return res

    @staticmethod
    def get_organization_detail(org_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role")
        user_org_id = user.get("organizationId")

        if role != "super_admin" and user_org_id != org_id:
            raise HTTPException(status_code=403, detail="عدم دسترسی به سازمان دیگر.")

        org = db.query(OrganizationModel).filter(OrganizationModel.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="سازمان یافت نشد.")

        teams = db.query(TeamModel).filter(TeamModel.organization_id == org_id).all()
        users = db.query(UserModel).filter(UserModel.organization_id == org_id).all()
        total_used = OrganizationService.get_organization_used_tokens(db, org_id)

        return {
            "organization": org.to_dict(total_used_tokens=total_used),
            "teams": [t.to_dict() for t in teams],
            "users": [u.to_dict() for u in users],
        }

    @staticmethod
    def create_organization(payload: CreateOrgRequest, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        if user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="تنها ادمین راس (Super Admin) مجاز به تعریف سازمان جدید است.")

        org_id = f"org_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        new_org = OrganizationModel(
            id=org_id,
            name=payload.name,
            code=payload.code or payload.name[:3].upper(),
            token_limit=payload.tokenLimit or 10000000,
            created_at=now,
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)
        return new_org.to_dict()

    @staticmethod
    def update_organization(org_id: str, payload: UpdateOrgRequest, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role")
        if role != "super_admin" and user.get("organizationId") != org_id:
            raise HTTPException(status_code=403, detail="عدم دسترسی برای ویرایش سازمان.")

        org = db.query(OrganizationModel).filter(OrganizationModel.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="سازمان یافت نشد.")

        if payload.name:
            org.name = payload.name
        if payload.code:
            org.code = payload.code
        if payload.tokenLimit is not None:
            org.token_limit = payload.tokenLimit
        db.commit()
        db.refresh(org)
        return org.to_dict()

    @staticmethod
    def delete_organization(org_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        if user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="عدم دسترسی برای حذف سازمان.")
        org = db.query(OrganizationModel).filter(OrganizationModel.id == org_id).first()
        if org:
            team_ids = [t.litellm_team_id or f"{t.organization_id}:{t.id}" for t in org.teams]
            if team_ids:
                litellm_client.delete_teams(team_ids)
            db.delete(org)
            db.commit()
        return {"deleted": True, "id": org_id}


organization_service = OrganizationService()
