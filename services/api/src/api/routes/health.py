"""Health probe endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe for Coolify / load balancers."""
    return {"status": "ok"}
