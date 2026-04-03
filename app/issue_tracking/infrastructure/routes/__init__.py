"""Issue tracking routes package — one module per resource."""

from app.issue_tracking.infrastructure.routes.comments import router as comment_router
from app.issue_tracking.infrastructure.routes.issues import router as issue_router
from app.issue_tracking.infrastructure.routes.projects import router as project_router

__all__ = ["comment_router", "issue_router", "project_router"]
