"""
Authentication API routes.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user
from app.auth.service import auth_service
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.schemas.common import StatusResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    return auth_service.login(email=payload.email, password=payload.password, response=response, db=db)


@router.get("/me", response_model=MeResponse)
async def get_me(user: Dict[str, Any] = Depends(get_optional_user)):
    if not user:
        raise HTTPException(status_code=401, detail="کاربر احراز هویت نشده است.")
    return {"user": user}


@router.post("/logout", response_model=StatusResponse)
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_token = request.cookies.get("sovereign_session") or request.headers.get("x-session-token")
    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else None

    tokens = [t for t in [session_token, bearer_token] if t]
    return auth_service.logout(tokens=tokens, response=response, db=db)


@router.post("/signup")
async def signup():
    raise HTTPException(
        status_code=403,
        detail="ثبت‌نام مستقیم غیرفعال است. نام‌نویسی کاربران توسط مدیران سیستم و سازمان انجام می‌گیرد.",
    )
