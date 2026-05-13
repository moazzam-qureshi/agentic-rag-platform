"""FastAPI app entry-point.

Wiring order matters:
1. Set the Dramatiq broker BEFORE importing any module that defines an actor.
2. Apply middleware (CORS, trusted-proxy) so request.state.client_ip exists.
3. Install slowapi limiter and exception handler.
4. Register routes.
"""

# ruff: noqa: I001  — `from api import broker` must precede route imports
# that transitively pull in shared.tasks actor decorations.

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

# IMPORTANT: import broker first so dramatiq.set_broker runs before any
# `@dramatiq.actor` decorators are evaluated via `shared.tasks` imports.
from api import broker  # noqa: F401
from api.config import settings
from api.routes import chat, documents, health, jobs, upload
from shared.guardrails.proxy import TrustedProxyMiddleware
from shared.guardrails.rate_limit import build_limiter, rate_limit_exceeded_response

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="DocuAI",
    description="Agentic RAG over your documents — vision-LLM page extraction, hybrid search, cited answers.",
    version="0.1.0",
)

# === Middleware ===
# Trusted-proxy must run BEFORE rate-limiting so the limiter sees the real IP.
app.add_middleware(
    TrustedProxyMiddleware,
    trusted_proxies=settings.trusted_proxies,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo: open. Production deploys tighten to the web origin.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Rate limiter ===
limiter = build_limiter(
    redis_url=settings.redis_url,
    default_limits=[
        f"{settings.rate_limit_per_hour}/hour",
        f"{settings.rate_limit_per_day}/day",
    ],
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return rate_limit_exceeded_response(request, exc)


# === Routes ===
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(chat.router)


@app.on_event("startup")
async def _startup() -> None:
    logger.info(
        "docuai_api_starting",
        service=settings.service_name,
        log_level=settings.log_level,
        rate_limit_hour=settings.rate_limit_per_hour,
        rate_limit_day=settings.rate_limit_per_day,
        upload_max_per_ip_per_day=settings.upload_max_per_ip_per_day,
        upload_max_pages_per_doc=settings.upload_max_pages_per_doc,
        document_ttl_hours=settings.document_ttl_hours,
        turnstile_enabled=bool(settings.turnstile_secret),
    )
