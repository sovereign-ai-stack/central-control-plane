"""
User business logic service.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.integrations.litellm import litellm_client
from app.models.team import TeamModel
from app.models.user import UserModel
from app.schemas.user import CreateUserRequest, UpdateUserRequest


class UserService:
    @staticmethod
    def list_users(
        caller: Dict[str, Any],
        organization_id: Optional[str],
        team_id: Optional[str],
        role_filter: Optional[str],
        db: Session,
    ) -> List[Dict[str, Any]]:
        caller_role = caller.get("role")
        caller_org = caller.get("organizationId")
        caller_team = caller.get("teamId")

        query = db.query(UserModel)
        if caller_role == "super_admin":
            if organization_id:
                query = query.filter(UserModel.organization_id == organization_id)
            if team_id:
                query = query.filter(UserModel.team_id == team_id)
        elif caller_role == "org_admin":
            query = query.filter(UserModel.organization_id == caller_org)
            if team_id:
                query = query.filter(UserModel.team_id == team_id)
        elif caller_role == "team_admin":
            query = query.filter(UserModel.team_id == caller_team)
        else:
            query = query.filter(UserModel.id == caller.get("id"))

        if role_filter:
            query = query.filter(UserModel.role == role_filter)

        users = query.all()
        return [u.to_dict() for u in users]

    @staticmethod
    def create_user(payload: CreateUserRequest, caller: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = caller.get("role")
        caller_org = caller.get("organizationId")
        caller_team = caller.get("teamId")

        email = payload.email.strip().lower()
        existing = db.query(UserModel).filter(UserModel.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="کاربری با این ایمیل از قبل در سیستم وجود دارد.")

        target_org = payload.organizationId
        target_team = payload.teamId
        target_role = payload.role

        if role == "super_admin":
            pass
        elif role == "org_admin":
            if target_role == "super_admin":
                raise HTTPException(status_code=403, detail="شما مجاز به ایجاد کاربر Super Admin نیستید.")
            target_org = caller_org
        elif role == "team_admin":
            if target_role in ["super_admin", "org_admin", "team_admin"]:
                raise HTTPException(status_code=403, detail="شما تنها مجاز به ایجاد کاربر عادی (User) در تیم خود هستید.")
            target_org = caller_org
            target_team = caller_team
            target_role = "user"
        else:
            raise HTTPException(status_code=403, detail="شما دسترسی ایجاد کاربر جدید را ندارید.")

        user_id = f"u_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        token_limit = payload.tokenLimit or 500000

        new_user = UserModel(
            id=user_id,
            email=email,
            name=payload.name,
            password=hash_password(payload.password),
            role=target_role,
            organization_id=target_org,
            team_id=target_team,
            is_active=True,
            litellm_synced=False,
            litellm_sync_error=None,
            used_tokens=0,
            token_limit=token_limit,
            created_at=now,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        UserService._sync_user_instance_to_litellm(new_user, db)

        return new_user.to_dict()

    @staticmethod
    def _sync_user_instance_to_litellm(user_obj: UserModel, db: Session) -> Tuple[bool, Optional[str]]:
        litellm_team_id = None
        if user_obj.team_id:
            team_obj = db.query(TeamModel).filter(TeamModel.id == user_obj.team_id).first()
            if team_obj:
                litellm_team_id = team_obj.litellm_team_id or f"{team_obj.organization_id}:{team_obj.id}"

        sync_ok, sync_err = litellm_client.sync_user(
            user_id=user_obj.id,
            email=user_obj.email,
            litellm_team_id=litellm_team_id,
            token_limit=user_obj.token_limit,
            role=user_obj.role,
        )
        user_obj.litellm_synced = sync_ok
        user_obj.litellm_sync_error = sync_err
        db.commit()
        db.refresh(user_obj)
        return sync_ok, sync_err

    @staticmethod
    def update_user(user_id: str, payload: UpdateUserRequest, caller: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = caller.get("role")
        target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if role != "super_admin":
            if role == "org_admin" and target_user.organization_id != caller.get("organizationId"):
                raise HTTPException(status_code=403, detail="عدم دسترسی به کاربر سازمان دیگر.")
            elif role == "team_admin" and target_user.team_id != caller.get("teamId"):
                raise HTTPException(status_code=403, detail="عدم دسترسی به کاربر تیم دیگر.")

        if payload.name:
            target_user.name = payload.name
        if payload.password and payload.password.strip():
            target_user.password = hash_password(payload.password.strip())
        if payload.tokenLimit is not None:
            target_user.token_limit = payload.tokenLimit
        if payload.isActive is not None:
            target_user.is_active = payload.isActive

        if role == "super_admin":
            if payload.role:
                target_user.role = payload.role
            if payload.organizationId is not None:
                target_user.organization_id = payload.organizationId or None
            if payload.teamId is not None:
                target_user.team_id = payload.teamId or None
        elif role == "org_admin":
            if payload.role and payload.role not in ["super_admin"]:
                target_user.role = payload.role
            if payload.teamId is not None:
                target_user.team_id = payload.teamId or None

        db.commit()
        db.refresh(target_user)

        UserService._sync_user_instance_to_litellm(target_user, db)

        return target_user.to_dict()

    @staticmethod
    def delete_user(user_id: str, caller: Dict[str, Any], db: Session) -> Dict[str, Any]:
        role = caller.get("role")
        target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
        if target_user.role == "super_admin":
            raise HTTPException(status_code=403, detail="امکان حذف حساب Super Admin ریشه وجود ندارد.")

        if role == "org_admin" and target_user.organization_id != caller.get("organizationId"):
            raise HTTPException(status_code=403, detail="عدم دسترسی برای حذف کاربر.")
        elif role == "team_admin" and target_user.team_id != caller.get("teamId"):
            raise HTTPException(status_code=403, detail="عدم دسترسی برای حذف کاربر.")

        litellm_team_id = None
        if target_user.team_id:
            team_obj = db.query(TeamModel).filter(TeamModel.id == target_user.team_id).first()
            if team_obj:
                litellm_team_id = team_obj.litellm_team_id or f"{team_obj.organization_id}:{team_obj.id}"

        litellm_client.delete_user(user_id=target_user.id, litellm_team_id=litellm_team_id)

        db.delete(target_user)
        db.commit()
        return {"deleted": True, "id": user_id}

    @staticmethod
    def sync_user_by_id(user_id: str, caller: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Manually triggers LiteLLM synchronization for a specific user."""
        role = caller.get("role")
        target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if role != "super_admin":
            if role == "org_admin" and target_user.organization_id != caller.get("organizationId"):
                raise HTTPException(status_code=403, detail="عدم دسترسی به کاربر سازمان دیگر.")
            elif role == "team_admin" and target_user.team_id != caller.get("teamId"):
                raise HTTPException(status_code=403, detail="عدم دسترسی به کاربر تیم دیگر.")

        sync_ok, sync_err = UserService._sync_user_instance_to_litellm(target_user, db)
        return {
            "success": sync_ok,
            "error": sync_err,
            "user": target_user.to_dict(),
        }

    @staticmethod
    def reconcile_all_users_with_litellm(caller: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Reconciles users with LiteLLM proxy, retrying unsynced/all users to prevent silent drift.
        """
        role = caller.get("role")
        if role not in ["super_admin", "org_admin"]:
            raise HTTPException(status_code=403, detail="تنها مدیران سامانه مجاز به بازهمگام‌سازی کاربران هستند.")

        query = db.query(UserModel)
        if role == "org_admin":
            query = query.filter(UserModel.organization_id == caller.get("organizationId"))

        users = query.all()
        synced_count = 0
        failed_count = 0
        errors = []

        for u in users:
            sync_ok, sync_err = UserService._sync_user_instance_to_litellm(u, db)
            if sync_ok:
                synced_count += 1
            else:
                failed_count += 1
                errors.append({"userId": u.id, "email": u.email, "error": sync_err})

        return {
            "totalUsers": len(users),
            "syncedUsers": synced_count,
            "failedUsers": failed_count,
            "errors": errors,
        }


user_service = UserService()
