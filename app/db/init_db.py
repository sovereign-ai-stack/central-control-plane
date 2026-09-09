"""
Database initialization and seeding.
"""

import os
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy import inspect, text

from app.core.logging import logger
from app.core.security import hash_password, needs_rehash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    UserModel,
    OrganizationModel,
    TeamModel,
    DocumentModel,
    ConversationModel,
    McpKeyModel,
    ManagedModelModel,
)


def _auto_migrate_columns():
    """Inspects all tables and adds any missing columns defined on SQLAlchemy models."""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        with engine.connect() as conn:
            for table_name, table_obj in Base.metadata.tables.items():
                if table_name in existing_tables:
                    existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                    for col in table_obj.columns:
                        if col.name not in existing_cols:
                            # Derive column type string for SQLite
                            type_str = str(col.type.compile(engine.dialect))
                            default_clause = ""
                            if col.default is not None and col.default.is_scalar:
                                default_clause = f" DEFAULT '{col.default.arg}'"
                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {type_str}{default_clause}"
                            logger.info(f"🔄 Migrating DB: adding column {col.name} to table {table_name}...")
                            conn.execute(text(alter_sql))
            conn.commit()
    except Exception as e:
        logger.warning(f"Database auto-migration warning: {e}")


def init_db():
    """Initializes tables, migrates missing columns, and seeds initial root Super Admin."""
    if str(engine.url).startswith("sqlite"):
        try:
            with engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL;"))
                conn.execute(text("PRAGMA synchronous=NORMAL;"))
                conn.execute(text("PRAGMA busy_timeout=30000;"))
                conn.commit()
        except Exception as e:
            logger.debug(f"SQLite PRAGMA tuning notice: {e}")

    Base.metadata.create_all(bind=engine)
    _auto_migrate_columns()
    db = SessionLocal()
    try:
        super_admin = db.query(UserModel).filter(UserModel.email == "admin@sovereign.local").first()
        admin_plain_password = os.getenv("ADMIN_INITIAL_PASSWORD", "admin")

        if not super_admin:
            now = datetime.now(timezone.utc).isoformat()
            root_user = UserModel(
                id="u_super_admin",
                email="admin@sovereign.local",
                name="مهدی جعفری",
                password=hash_password(admin_plain_password),
                role="super_admin",
                organization_id=None,
                team_id=None,
                is_active=True,
                used_tokens=0,
                token_limit=50000000,
                created_at=now,
            )
            db.add(root_user)
            db.commit()
            if admin_plain_password == "admin":
                logger.warning("⚠️ Super Admin seeded with default password 'admin'. Please set ADMIN_INITIAL_PASSWORD in production!")
            logger.info("👑 Initial Super Admin (مهدی جعفری) seeded to persistent DB with secure PBKDF2 hash.")
        elif needs_rehash(super_admin.password):
            # If root admin exists with legacy plaintext password, upgrade to PBKDF2 hash
            super_admin.password = hash_password(super_admin.password)
            db.commit()
            logger.info("🔒 Upgraded existing Super Admin password to secure PBKDF2 hash.")

        # Re-hydrate all persistent documents into RAG vector index asynchronously in background
        import threading
        def _bg_rehydrate():
            bg_db = SessionLocal()
            try:
                from app.services.document_service import document_service
                document_service.ensure_all_documents_indexed(bg_db)
            finally:
                bg_db.close()

        threading.Thread(target=_bg_rehydrate, daemon=True).start()
    finally:
        db.close()
