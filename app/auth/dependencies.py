"""
Authentication dependencies for resolving user sessions and enforcing RBAC.
"""

from typing import Any, Dict, Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import SessionModel, UserModel


def resolve_user(request: Request, db: Session, required: bool = True) -> Optional[Dict[str, Any]]:
    """Resolves authenticated user from Bearer header or cookie / x-session-token."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        sess = db.query(SessionModel).filter(SessionModel.token == token).first()
        if sess:
            usr = db.query(UserModel).filter(UserModel.email == sess.user_email).first()
            if usr and usr.is_active:
                return usr.to_dict()

    session_token = request.cookies.get("sovereign_session") or request.headers.get("x-session-token")
    if session_token:
        sess = db.query(SessionModel).filter(SessionModel.token == session_token).first()
        if sess:
            usr = db.query(UserModel).filter(UserModel.email == sess.user_email).first()
            if usr and usr.is_active:
                return usr.to_dict()

    if required:
        raise HTTPException(status_code=401, detail="نشست کاربری شما منقضی شده است. لطفاً مجدداً وارد شوید.")
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Dependency ensuring request has a valid authenticated user."""
    return resolve_user(request, db, required=True)


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[Dict[str, Any]]:
    """Dependency resolving user if available without raising 401."""
    return resolve_user(request, db, required=False)
