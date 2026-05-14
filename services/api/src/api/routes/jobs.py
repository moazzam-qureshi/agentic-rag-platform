"""GET /jobs/:document_id — ingestion progress polling for the upload UI."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from shared.db_models import Document, ProcessingLog
from shared.guardrails.client_ip import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/jobs/{document_id}")
async def get_ingestion_status(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current ingestion status + recent log messages.

    The frontend polls this every ~1.5s while a doc is processing so the user
    sees live progress ("Parsing with VLM...", "8/14 pages indexed...").
    """
    client_ip = get_client_ip(request)

    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.client_ip != client_ip:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Last 20 log lines, most recent first.
    log_stmt = (
        select(ProcessingLog)
        .where(ProcessingLog.document_id == document_id)
        .order_by(ProcessingLog.created_at.desc())
        .limit(20)
    )
    log_result = await db.execute(log_stmt)
    logs = log_result.scalars().all()

    # Derive a structured progress signal from log details so the UI can
    # render a per-page bar without parsing prose.
    #
    # The worker writes:
    #   details = {"total_pages": N}                 (once, at parse start)
    #   details = {"page_number": k, "total_pages": N}  (per page completed)
    progress_pages_done = 0
    progress_total_pages = 0
    for log in logs:  # newest -> oldest; first matching wins
        details = log.details or {}
        if "total_pages" in details:
            if progress_total_pages == 0:
                progress_total_pages = int(details["total_pages"])
            if "page_number" in details and progress_pages_done == 0:
                progress_pages_done = int(details["page_number"])
            if progress_total_pages and progress_pages_done:
                break

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "page_count": doc.page_count,
        "error_message": doc.error_message,
        "progress": {
            "pages_done": progress_pages_done,
            "total_pages": progress_total_pages,
        },
        "logs": [
            {
                "level": log.level.value,
                "message": log.message,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in reversed(logs)  # oldest first for UI display
        ],
    }
