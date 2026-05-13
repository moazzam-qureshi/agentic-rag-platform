"""Cloudflare Turnstile token verification.

Turnstile is Cloudflare's free CAPTCHA alternative. We attach it to the
single most expensive endpoint per project (uploads here) so scripted
abuse hits a wall while real humans see zero friction.

Flow:
1. Frontend renders the Turnstile widget with the site key.
2. Widget produces a token on user interaction (or invisibly if the user
   already passed Cloudflare's heuristics).
3. Frontend sends the token alongside the upload.
4. This function verifies the token with Cloudflare's siteverify endpoint.
5. Reject on failure.

The siteverify endpoint is documented at:
https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
"""

import httpx
import structlog

logger = structlog.get_logger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(
    token: str,
    secret: str,
    client_ip: str | None = None,
    timeout: float = 5.0,
) -> bool:
    """Verify a Turnstile token. Returns True if valid, False otherwise.

    If `secret` is empty (e.g. local dev with TURNSTILE_SECRET=""), this
    returns True — Turnstile is opt-in. Production deploys MUST set a real
    secret in Coolify env vars.
    """
    if not secret:
        logger.warning("turnstile_secret_missing_skipping_verification")
        return True

    if not token:
        return False

    data = {"secret": secret, "response": token}
    if client_ip:
        data["remoteip"] = client_ip

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(SITEVERIFY_URL, data=data)
            response.raise_for_status()
            payload = response.json()
    except Exception as e:
        logger.error("turnstile_verification_failed", error=str(e))
        return False

    success = bool(payload.get("success"))
    if not success:
        logger.warning(
            "turnstile_token_rejected",
            error_codes=payload.get("error-codes", []),
        )
    return success
