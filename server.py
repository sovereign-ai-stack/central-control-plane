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
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
