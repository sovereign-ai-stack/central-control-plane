"""
Admin Teams API routes.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import DeleteResponse
from app.schemas.team import (
    CreateTeamRequest,
    UpdateTeamRequest,
    TeamListResponse,
    TeamDetailResponse,
)
from app.services.team_service import team_service

router = APIRouter(prefix="/admin/teams", tags=["Admin Teams"])


@router.get("", response_model=TeamListResponse)
async def list_teams(
    organizationId: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teams = team_service.list_teams(user=user, organization_id=organizationId, db=db)
    return {"teams": teams}


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team_detail(team_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return team_service.get_team_detail(team_id=team_id, user=user, db=db)


@router.post("", response_model=Dict[str, Any])
async def create_team(payload: CreateTeamRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return team_service.create_team(payload=payload, user=user, db=db)


@router.put("/{team_id}", response_model=Dict[str, Any])
async def update_team(team_id: str, payload: UpdateTeamRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return team_service.update_team(team_id=team_id, payload=payload, user=user, db=db)


@router.delete("/{team_id}", response_model=DeleteResponse)
async def delete_team(team_id: str, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    return team_service.delete_team(team_id=team_id, user=user, db=db)
