"""Main FastAPI application — DDD bounded-context wiring."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import setup_logging
from app.identity.infrastructure.routes import router as identity_router
from app.issue_tracking.infrastructure.routes import (
    comment_router,
    issue_router,
    project_router,
)
from app.notifications.infrastructure.connection_manager import ConnectionManager
from app.notifications.infrastructure.routes import router as notifications_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan — initialize and clean up resources."""
    app.state.connection_manager = ConnectionManager()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Security middleware - only in production
if not settings.DEBUG and settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers from bounded contexts
app.include_router(identity_router, prefix="/auth")
app.include_router(project_router, prefix="/projects")
app.include_router(issue_router, prefix="/issues")
app.include_router(comment_router, prefix="/issues/{issue_id}/comments")
app.include_router(notifications_router, prefix="/notifications")


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    """Root endpoint with welcome message."""
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Health check endpoint with database connectivity verification."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
    }
