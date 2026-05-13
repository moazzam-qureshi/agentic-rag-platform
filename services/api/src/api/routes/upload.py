"""POST /upload — Turnstile-gated, page-capped, async-ingested."""

import base64
import os
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db.session import get_db
from shared.db_models import Document, DocumentStatus
from shared.guardrails.client_ip import get_client_ip
from shared.guardrails.cost_ceiling import consume_cost_units, cost_remaining
from shared.guardrails.turnstile import verify_turnstile_token
from shared.indexing.page_extractor import (
    SUPPORTED_EXTENSIONS,
    get_page_count,
)
from shared.tasks import ingest_uploaded_document

logger = structlog.get_logger(__name__)

router = APIRouter()

# Sync Redis client for cost-ceiling checks (Lua scripts work fine via sync client)
_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    turnstile_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept a document upload, validate it, enqueue async VLM ingestion.

    Guardrails applied in order:
    1. Turnstile (Cloudflare) token verification.
    2. File-type whitelist (PDF, DOCX, DOC, XLSX, XLS).
    3. Per-IP daily upload count ceiling.
    4. Page-count ceiling per doc.
    5. Per-IP daily VLM-page cost ceiling.

    Returns the created document_id + job_id so the frontend can poll
    /jobs/:id for ingestion progress.
    """
    client_ip = get_client_ip(request)

    # 1. Turnstile verification
    if settings.turnstile_secret:
        ok = await verify_turnstile_token(
            token=turnstile_token,
            secret=settings.turnstile_secret,
            client_ip=client_ip,
        )
        if not ok:
            raise HTTPException(
                status_code=403,
                detail="Turnstile verification failed. Refresh and try again.",
            )

    # 2. File-type whitelist
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {suffix}. "
            f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    # 3. Per-IP daily upload count ceiling
    redis = _get_redis()
    upload_remaining = cost_remaining(
        redis,
        ip=client_ip,
        max_units=settings.upload_max_per_ip_per_day,
        namespace="docuai:uploads",
    )
    if upload_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've hit the demo limit of "
                f"{settings.upload_max_per_ip_per_day} uploads per day. "
                "Try again tomorrow, or get in touch for a self-hosted version."
            ),
        )

    # 4. Page-count ceiling per doc
    # Use the cheap page-counter (skips VLM, just renders count from PyMuPDF)
    try:
        page_count_estimate = get_page_count(
            file_content=content,
            filename=file.filename or "upload",
        )
    except Exception as e:
        logger.warning("page_count_estimate_failed", error=str(e))
        # If we can't read it at all, reject
        raise HTTPException(
            status_code=400,
            detail=f"Could not read document: {e}",
        )

    if page_count_estimate == 0:
        raise HTTPException(
            status_code=400,
            detail="Document appears to have no pages.",
        )

    if page_count_estimate > settings.upload_max_pages_per_doc:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Demo limit: {settings.upload_max_pages_per_doc} pages per "
                f"document. This file has {page_count_estimate} pages."
            ),
        )

    # 5. Per-IP daily VLM-page cost ceiling
    # Each page costs roughly the same in VLM tokens; we use pages as the unit.
    max_pages_per_day = settings.upload_max_per_ip_per_day * settings.upload_max_pages_per_doc
    accepted = consume_cost_units(
        redis,
        ip=client_ip,
        units=page_count_estimate,
        max_units=max_pages_per_day,
        namespace="docuai:vlm_pages",
    )
    if not accepted:
        raise HTTPException(
            status_code=429,
            detail=("You've hit the daily VLM page-processing limit. Try again tomorrow."),
        )

    # All guardrails passed — also bump the upload count ceiling.
    consume_cost_units(
        redis,
        ip=client_ip,
        units=1,
        max_units=settings.upload_max_per_ip_per_day,
        namespace="docuai:uploads",
    )

    # Create the Document row.
    doc = Document(
        filename=file.filename or "upload",
        status=DocumentStatus.PENDING.value,
        client_ip=client_ip,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.document_ttl_hours),
        page_count=0,  # filled in by the worker on completion
        metadata_={"source": "upload", "content_type": file.content_type or ""},
    )
    db.add(doc)
    await db.flush()
    document_id = doc.id

    # Enqueue async VLM ingestion.
    file_b64 = base64.b64encode(content).decode("ascii")
    msg = ingest_uploaded_document.send(
        document_id=document_id,
        file_content_b64=file_b64,
        filename=doc.filename,
        client_ip=client_ip,
        ttl_hours=settings.document_ttl_hours,
    )

    logger.info(
        "upload_accepted",
        document_id=document_id,
        filename=doc.filename,
        page_count=page_count_estimate,
        client_ip=client_ip,
        message_id=msg.message_id,
    )

    return {
        "document_id": document_id,
        "filename": doc.filename,
        "page_count_estimate": page_count_estimate,
        "status": DocumentStatus.PENDING.value,
        "message_id": msg.message_id,
    }
