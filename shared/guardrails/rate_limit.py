"""Redis-backed per-IP rate limiter (slowapi).

We key on the *trusted* client IP set by TrustedProxyMiddleware, not
request.client.host, so spoofed X-Forwarded-For headers cannot bypass.

Why slowapi + Redis: in-memory limits don't share state across uvicorn
workers and reset on every container restart. Redis is the natural shared
store and we already run it for the worker queue.
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.guardrails.client_ip import get_client_ip


def _trusted_ip_key(request: Request) -> str:
    """Key function: rate-limit by the trusted client IP."""
    return get_client_ip(request)


def build_limiter(redis_url: str, default_limits: list[str] | None = None) -> Limiter:
    """Build a slowapi Limiter backed by Redis, keyed on trusted IP.

    Args:
        redis_url: redis://host:port/db
        default_limits: optional global defaults (e.g. ["100/day"])
    """
    return Limiter(
        key_func=_trusted_ip_key,
        storage_uri=redis_url,
        default_limits=default_limits or [],
        strategy="moving-window",  # sliding window — smoother than fixed
    )


def rate_limit_exceeded_response(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Polite JSON response when rate limited."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limited",
            "message": (
                "You've hit the demo rate limit. This is a free public demo with "
                "guardrails to keep costs in check. Try again later, or get in "
                "touch if you'd like a self-hosted version."
            ),
            "retry_after_seconds": getattr(exc, "retry_after", None),
        },
        headers={"Retry-After": str(int(getattr(exc, "retry_after", 60) or 60))},
    )
