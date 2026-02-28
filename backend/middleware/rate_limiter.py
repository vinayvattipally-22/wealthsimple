"""Rate limiting middleware using SlowAPI."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _key_func(request: Request) -> str:
    """Rate limit by API key header if present, else by IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    return get_remote_address(request)


limiter = Limiter(key_func=_key_func)

# Rate limit decorators for different endpoint types
UPLOAD_LIMIT = "30/minute"
READ_LIMIT = "60/minute"
ANALYSIS_LIMIT = "10/minute"
