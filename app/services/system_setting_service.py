"""
System Setting Service for managing global cluster configurations.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.system_setting import SystemSettingModel


class SystemSettingService:
    @staticmethod
    def get_value(key: str, default: str = "", db: Optional[Session] = None) -> str:
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            row = db.query(SystemSettingModel).filter(SystemSettingModel.key == key).first()
            return row.value if row else default
        finally:
            if close_db:
                db.close()

    @staticmethod
    def get_bool(key: str, default: bool = False, db: Optional[Session] = None) -> bool:
        val = SystemSettingService.get_value(key, str(default).lower(), db)
        return val.lower() in ("true", "1", "yes", "on")

    @staticmethod
    def set_value(key: str, value: str, db: Optional[Session] = None) -> str:
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            now = datetime.now(timezone.utc).isoformat()
            row = db.query(SystemSettingModel).filter(SystemSettingModel.key == key).first()
            if not row:
                row = SystemSettingModel(key=key, value=value, updated_at=now)
                db.add(row)
            else:
                row.value = value
                row.updated_at = now
            db.commit()
            return row.value
        finally:
            if close_db:
                db.close()
