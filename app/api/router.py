"""
Master API Router.
Mounts all route modules under the configured PREFIX.
"""

from fastapi import APIRouter

from app.api.routes.admin_dashboard import router as admin_dashboard_router
from app.api.routes.admin_documents import router as admin_documents_router
from app.api.routes.admin_models import router as admin_models_router
from app.api.routes.admin_organizations import router as admin_organizations_router
from app.api.routes.admin_teams import router as admin_teams_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router
from app.api.routes.internal_rag import router as internal_rag_router
from app.core.config import settings

api_router = APIRouter()

# Mount prefix routes
prefix_router = APIRouter(prefix=settings.PREFIX)
prefix_router.include_router(auth_router)
prefix_router.include_router(admin_organizations_router)
prefix_router.include_router(admin_teams_router)
prefix_router.include_router(admin_users_router)
prefix_router.include_router(admin_documents_router)
prefix_router.include_router(admin_dashboard_router)
prefix_router.include_router(admin_models_router)
prefix_router.include_router(chat_router)
prefix_router.include_router(conversations_router)
prefix_router.include_router(internal_rag_router)

# Include both prefix router and root health check
api_router.include_router(prefix_router)
api_router.include_router(health_router)
