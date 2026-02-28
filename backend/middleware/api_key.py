"""Optional API key authentication middleware."""
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Exempt paths that don't require API key
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/api/auth/register", "/api/auth/login"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header if API_KEYS env var is configured.

    When API_KEYS is not set, all requests pass through (development mode).
    When set, it should be a comma-separated list of valid keys.
    """

    def __init__(self, app, api_keys: list[str] | None = None):
        super().__init__(app)
        if api_keys is None:
            raw = os.getenv("API_KEYS", "")
            self.api_keys = [k.strip() for k in raw.split(",") if k.strip()] if raw else []
        else:
            self.api_keys = api_keys

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no keys configured (development mode)
        if not self.api_keys:
            return await call_next(request)

        # Exempt specific paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Check API key
        provided_key = request.headers.get("X-API-Key")
        if not provided_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header"},
            )
        if provided_key not in self.api_keys:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        return await call_next(request)
