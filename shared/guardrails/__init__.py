"""Guardrails — engineering invariant shared across all portfolio projects.

Layered defense for public-facing demo endpoints:
1. Trusted-proxy middleware: only honor X-Forwarded-For from Coolify's Traefik.
2. Redis-backed per-IP sliding-window rate limit (slowapi).
3. Per-IP daily cost ceiling (Redis counter, decremented per expensive op).
4. Cloudflare Turnstile verification (gates the most expensive endpoint).
5. LLM-call wrapper that caps max_tokens and logs usage.
6. 24h auto-deletion of uploaded content (cleanup job).

The CONTRACT is identical across projects; each project re-implements in its
chosen stack. This module is the Python reference implementation.
"""

from shared.guardrails.client_ip import get_client_ip
from shared.guardrails.cost_ceiling import (
    consume_cost_units,
    cost_remaining,
)
from shared.guardrails.proxy import TrustedProxyMiddleware
from shared.guardrails.rate_limit import (
    build_limiter,
    rate_limit_exceeded_response,
)
from shared.guardrails.turnstile import verify_turnstile_token

__all__ = [
    "get_client_ip",
    "consume_cost_units",
    "cost_remaining",
    "TrustedProxyMiddleware",
    "build_limiter",
    "rate_limit_exceeded_response",
    "verify_turnstile_token",
]
