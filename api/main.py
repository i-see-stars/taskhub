from fastapi import FastAPI

from api.auth.views import router as auth_router
from api.core.config import settings
from api.projects.routes import router as projects_router

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(projects_router)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug")
async def debug():
    return {"debug": settings.DEBUG}
