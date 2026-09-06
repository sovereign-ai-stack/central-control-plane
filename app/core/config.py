"""
Application Settings & Configuration.
Loads environment variables and sets defaults for the Sovereign Central Control Plane.
"""

import os
from typing import Any, Dict


class Settings:
    PROJECT_NAME: str = "Sovereign AI Central Control Plane"
    VERSION: str = "2.0.0"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sovereign_control_plane.db")
    LITELLM_URL: str = os.getenv("LITELLM_URL", "http://localhost:4000")
    LITELLM_MASTER_KEY: str = os.getenv("LITELLM_MASTER_KEY", "sk-lite-master-1234")
    REGISTRY_URL: str = os.getenv("REGISTRY_URL", "http://localhost:8200")
    SEMANTIC_URL: str = os.getenv("SEMANTIC_URL", "http://localhost:8300")

    # In-Process RAG Subsystem Configuration
    RAG_VECTOR_STORE_BACKEND: str = os.getenv("RAG_VECTOR_STORE_BACKEND", "memory")
    RAG_WEAVIATE_URL: str = os.getenv("RAG_WEAVIATE_URL", "http://localhost:18080")
    RAG_EMBEDDING_DEVICE: str = os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
    RAG_EMBEDDING_BACKEND: str = os.getenv("RAG_EMBEDDING_BACKEND", "stub")

    APP_SECRET_PATH: str = os.getenv("APP_SECRET_PATH", "").strip("/")

    @property
    def PREFIX(self) -> str:
        return f"/{self.APP_SECRET_PATH}/api" if self.APP_SECRET_PATH else "/api"

    DB_LIMITS: Dict[str, Any] = {
        "maxRps": 20,
        "defaultRps": 5,
        "inferenceConcurrency": 32,
        "maxInputChars": 8000,
        "maxOutputTokens": 4096,
        "maxPdfPages": 20,
        "perAccountTokenLimit": 500000,
        "workspaceTokenLimit": 20000000,
        "messagesPerHour": 120,
    }


settings = Settings()
