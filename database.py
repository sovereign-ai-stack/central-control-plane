"""
Production Database Layer Re-export (Backwards Compatibility Module).
Re-exports Base, SessionLocal, engine, get_db, init_db, and all models from app.db and app.models.
"""

from app.db import Base, DATABASE_URL, SessionLocal, engine, get_db, init_db
from app.models import (
    ConversationModel,
    DocumentModel,
    McpKeyModel,
    OrganizationModel,
    SessionModel,
    TeamModel,
    UserModel,
)

# Auto-initialize tables immediately
init_db()

__all__ = [
    "Base",
    "DATABASE_URL",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
    "OrganizationModel",
    "TeamModel",
    "UserModel",
    "SessionModel",
    "DocumentModel",
    "ConversationModel",
    "McpKeyModel",
]
