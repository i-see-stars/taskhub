import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.auth.routes import router as auth_router
from app.api.core.config import settings
from app.api.core.logging import setup_logging
from app.api.issues.routes import router as issues_router
from app.api.projects.routes import router as projects_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(projects_router)
app.include_router(issues_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint with database connectivity verification."""
    from sqlalchemy import text

    from app.api.core.database import engine

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
