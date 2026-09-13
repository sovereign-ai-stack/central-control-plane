#!/usr/bin/env python3
"""
Enterprise Central AI Gateway & Multi-Tenant Control Plane.
Thin application entrypoint.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing persistent database schema...")
    init_db()

    # Reconcile managed models with LiteLLM in background (non-blocking)
    import threading
    def _bg_model_reconcile():
        import time
        time.sleep(5)  # صبر کن Gateway کاملاً بالا بیاد
        try:
            from app.db.session import SessionLocal
            from app.services.managed_model_service import ManagedModelService
            bg_db = SessionLocal()
            try:
                result = ManagedModelService.reconcile_all_models_with_litellm(bg_db)
                synced = result.get("active", 0)
                total = synced + result.get("purged", 0)
                if total > 0:
                    logger.info(f"✅ Model reconciliation: {synced}/{total} models synced to LiteLLM")
                else:
                    logger.info("ℹ️  No managed models found in DB to sync (normal on first run)")
            finally:
                bg_db.close()
        except Exception as e:
            logger.warning(f"⚠️  Background model reconciliation failed (non-critical): {e}")

    threading.Thread(target=_bg_model_reconcile, daemon=True).start()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

cors_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if cors_origins_env:
    origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting Sovereign AI Gateway API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
