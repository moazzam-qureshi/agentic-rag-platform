"""GET /documents, DELETE /documents/:id — per-IP document management."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.opensearch_store import get_page_store
from api.db.session import get_db
from shared.db_models import Document, DocumentStatus
from shared.guardrails.client_ip import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/documents")
async def list_documents(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List the calling IP's documents.

    Returns only this client's own uploads — no cross-IP visibility.
    """
    client_ip = get_client_ip(request)

    stmt = (
        select(Document)
        .where(Document.client_ip == client_ip)
        .where(Document.status != DocumentStatus.DELETED.value)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "status": d.status,
                "page_count": d.page_count,
                "created_at": d.created_at.isoformat(),
                "expires_at": d.expires_at.isoformat() if d.expires_at else None,
                "error_message": d.error_message,
            }
            for d in docs
        ]
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete the document for the caller. Also purges OpenSearch pages."""
    client_ip = get_client_ip(request)

    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Only the uploader can delete their own doc.
    if doc.client_ip != client_ip:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove pages from OpenSearch index
    store = get_page_store()
    pages_deleted = store.delete_document(document_id)

    # Soft-delete the row (kept for audit; the daily cleanup hard-removes)
    doc.status = DocumentStatus.DELETED.value
    await db.flush()

    logger.info(
        "document_deleted",
        document_id=document_id,
        client_ip=client_ip,
        pages_deleted=pages_deleted,
    )

    return {
        "document_id": document_id,
        "pages_deleted": pages_deleted,
        "status": DocumentStatus.DELETED.value,
    }
