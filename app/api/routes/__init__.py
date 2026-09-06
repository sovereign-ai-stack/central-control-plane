"""
API Routes Package.
"""

from app.api.routes.auth import router as auth_router
from app.api.routes.admin_organizations import router as admin_organizations_router
from app.api.routes.admin_teams import router as admin_teams_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.admin_documents import router as admin_documents_router
from app.api.routes.admin_dashboard import router as admin_dashboard_router
from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router

__all__ = [
    "auth_router",
    "admin_organizations_router",
    "admin_teams_router",
    "admin_users_router",
    "admin_documents_router",
    "admin_dashboard_router",
    "chat_router",
    "conversations_router",
    "health_router",
]
