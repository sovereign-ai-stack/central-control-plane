"""
Database session and connection management.
Optimized for production concurrency with PostgreSQL connection pooling and resilient SQLite configuration.
"""

import os
from typing import Any, Dict, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
is_sqlite = DATABASE_URL.startswith("sqlite")

# Engine connection parameters
connect_args: Dict[str, Any] = {"check_same_thread": False, "timeout": 30.0} if is_sqlite else {}

engine_kwargs: Dict[str, Any] = {
    "echo": False,
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

# Production PostgreSQL connection pool configuration
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": float(os.getenv("DB_POOL_TIMEOUT", "30.0")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions with guaranteed cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
