"""Request logging middleware for structured request/response logging."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
SKIP_LOGGING_PATHS = {"/health"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request with structured metadata.

    Logs: request_id, method, path, status_code, duration_ms, user_agent, client_ip.
    Does NOT log query strings, request/response bodies, or auth headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request, measure duration, and log metadata."""
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        start_time = time.monotonic()

        response = await call_next(request)

        if request.url.path in SKIP_LOGGING_PATHS:
            return response

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.info(
            "request completed",
            extra={
                "extra": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "user_agent": request.headers.get("user-agent", ""),
                    "client_ip": request.client.host if request.client else "",
                }
            },
        )

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
