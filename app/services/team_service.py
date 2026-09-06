"""
Team business logic service.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.integrations.litellm import litellm_client
from app.models.document import DocumentModel
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.models.user import UserModel
from app.schemas.team import CreateTeamRequest, UpdateTeamRequest


class TeamService:
    @staticmethod
    def list_teams(user: Dict[str, Any], organization_id: Optional[str], db: Session) -> List[Dict[str, Any]]:
        role = user.get("role", "super_admin")
        user_org_id = user.get("organizationId")
        user_team_id = user.get("teamId")

        query = db.query(TeamModel)
        if role == "super_admin":
            if organization_id:
                query = query.filter(TeamModel.organization_id == organization_id)
        elif role == "org_admin":
            query = query.filter(TeamModel.organization_id == user_org_id)
        else:
            query = query.filter(TeamModel.id == user_team_id)

        teams = query.all()
        return [t.to_dict() for t in teams]

    @staticmethod
    def get_team_detail(team_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role")
        user_org_id = user.get("organizationId")
        user_team_id = user.get("teamId")

        team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="تیم یافت نشد.")

        if role == "org_admin" and team.organization_id != user_org_id:
            raise HTTPException(status_code=403, detail="عدم دسترسی به تیم این سازمان.")
        elif role not in ["super_admin", "org_admin"] and team.id != user_team_id:
            raise HTTPException(status_code=403, detail="عدم دسترسی کافی.")

        members = db.query(UserModel).filter(UserModel.team_id == team_id).all()
        docs = db.query(DocumentModel).filter(
            DocumentModel.organization_id == team.organization_id,
            DocumentModel.team_id == team_id,
        ).all()

        return {
            "team": team.to_dict(),
            "members": [m.to_dict() for m in members],
            "documents": [
                d.to_dict(org_name=team.organization.name if team.organization else "", team_name=team.name)
                for d in docs
            ],
        }

    @staticmethod
    def create_team(payload: CreateTeamRequest, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role")
        user_org_id = user.get("organizationId")

        target_org = payload.organizationId
        if role == "org_admin":
            target_org = user_org_id
        elif role != "super_admin":
            raise HTTPException(status_code=403, detail="شما دسترسی ایجاد تیم جدید را ندارید.")

        org = db.query(OrganizationModel).filter(OrganizationModel.id == target_org).first()
        if not org:
            raise HTTPException(status_code=404, detail="سازمان مورد نظر یافت نشد.")

        team_id = f"team_{uuid.uuid4().hex[:6]}"
        litellm_team_id = f"{target_org}:{team_id}"
        now = datetime.now(timezone.utc).isoformat()

        new_team = TeamModel(
            id=team_id,
            organization_id=target_org,
            litellm_team_id=litellm_team_id,
            name=payload.name,
            token_limit=payload.tokenLimit or 2000000,
            used_tokens=0,
            rpm_limit=payload.rpmLimit or 100,
            tpm_limit=payload.tpmLimit or 100000,
            created_at=now,
        )
        db.add(new_team)
        db.commit()
        db.refresh(new_team)

        litellm_client.sync_team(
            litellm_team_id=litellm_team_id,
            team_alias=f"{org.name} - {payload.name}",
            max_budget=float(payload.tokenLimit or 2000000),
            rpm_limit=payload.rpmLimit or 100,
            tpm_limit=payload.tpmLimit or 100000,
            org_id=target_org,
        )

        return new_team.to_dict()

    @staticmethod
    def update_team(team_id: str, payload: UpdateTeamRequest, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role")
        team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="تیم یافت نشد.")

        if role == "org_admin" and team.organization_id != user.get("organizationId"):
            raise HTTPException(status_code=403, detail="عدم دسترسی به ویرایش تیم این سازمان.")
        elif role not in ["super_admin", "org_admin"]:
            raise HTTPException(status_code=403, detail="عدم دسترسی کافی.")

        if payload.name:
            team.name = payload.name
        if payload.tokenLimit is not None:
            team.token_limit = payload.tokenLimit
        if payload.rpmLimit is not None:
            team.rpm_limit = payload.rpmLimit
        if payload.tpmLimit is not None:
            team.tpm_limit = payload.tpmLimit

        db.commit()
        db.refresh(team)

        litellm_t_id = team.litellm_team_id or f"{team.organization_id}:{team.id}"
        org_name = team.organization.name if team.organization else ""
        litellm_client.update_team(
            litellm_team_id=litellm_t_id,
            team_alias=f"{org_name} - {team.name}",
            max_budget=float(team.token_limit),
            rpm_limit=team.rpm_limit,
            tpm_limit=team.tpm_limit,
        )

        return team.to_dict()

    @staticmethod
    def delete_team(team_id: str, user: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = user.get("role")
        team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="تیم یافت نشد.")

        if role == "org_admin" and team.organization_id != user.get("organizationId"):
            raise HTTPException(status_code=403, detail="عدم دسترسی برای حذف این تیم.")
        elif role not in ["super_admin", "org_admin"]:
            raise HTTPException(status_code=403, detail="عدم دسترسی کافی.")

        litellm_t_id = team.litellm_team_id or f"{team.organization_id}:{team.id}"
        litellm_client.delete_teams([litellm_t_id])

        db.delete(team)
        db.commit()
        return {"deleted": True, "id": team_id}


team_service = TeamService()
