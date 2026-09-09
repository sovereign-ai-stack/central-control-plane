"""
Authentication business logic service.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, Response
from sqlalchemy.orm import Session

from app.core.security import hash_password, needs_rehash, verify_password
from app.models.user import SessionModel, UserModel


class AuthService:
    @staticmethod
    def login(email: str, password: str, response: Response, db: Session) -> Dict[str, Any]:
        email_clean = email.strip().lower()
        user = db.query(UserModel).filter(UserModel.email == email_clean).first()
        if not user or not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="ایمیل یا گذرواژه وارد شده نامعتبر است.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="حساب کاربری شما توسط مدیر سازمان غیرفعال شده است.")

        # Seamless auto-migration: if user still has legacy plaintext password, upgrade to PBKDF2 hash
        if needs_rehash(user.password):
            user.password = hash_password(password)
            db.commit()

        session_token = f"sess_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        new_session = SessionModel(token=session_token, user_email=user.email, created_at=now)
        db.add(new_session)
        db.commit()

        response.set_cookie(
            key="sovereign_session",
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,
            path="/",
        )
        return {"token": session_token, "user": user.to_dict()}

    @staticmethod
    def logout(tokens: List[str], response: Response, db: Session) -> Dict[str, Any]:
        valid_tokens = [t for t in tokens if t]
        if valid_tokens:
            db.query(SessionModel).filter(SessionModel.token.in_(valid_tokens)).delete(synchronize_session=False)
            db.commit()

        response.delete_cookie(key="sovereign_session", path="/")
        return {"status": "logged_out"}


auth_service = AuthService()
