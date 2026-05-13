"""Dramatiq actor for ingesting an uploaded document.

This module is imported by BOTH the API (to send messages) and the worker
(to execute them). The broker must already be set via dramatiq.set_broker()
before this module is imported — each service handles that in its own
broker module.

The function body itself runs only inside the worker process. The API just
needs the actor to exist by name so `.send()` works.
"""

import asyncio
import base64
from datetime import UTC, datetime, timedelta

import dramatiq
import structlog
from sqlalchemy import select

from shared.db_models import (
    Document,
    DocumentStatus,
    JobStatus,
    JobType,
    LogLevel,
    ProcessingLog,
    SyncJob,
)
from shared.indexing.pipeline import PageLevelIndexer

logger = structlog.get_logger(__name__)


@dramatiq.actor(
    queue_name="documents",
    priority=5,
    max_retries=0,  # VLM calls cost real money; no auto-retries on failure
    time_limit=15 * 60 * 1000,  # 15 min hard cap per doc
)
def ingest_uploaded_document(
    document_id: str,
    file_content_b64: str,
    filename: str,
    client_ip: str | None = None,
    ttl_hours: int = 24,
) -> dict:
    """Worker entry-point: VLM-ingest an uploaded document, page by page.

    Args:
        document_id: UUID of the Document row already created by the API.
        file_content_b64: Base64-encoded file bytes.
        filename: Original filename for citation purposes.
        client_ip: Uploader's IP, captured for the 24h cleanup job.
        ttl_hours: Auto-delete after this many hours.

    Returns:
        Dict with document_id, status, page_count.
    """
    # Late imports — these modules pull in worker config / DB session, which
    # only exists inside the worker process at runtime.
    from worker.config import settings as wsettings
    from worker.db.session import get_db_session

    logger.info("ingest_uploaded_document", document_id=document_id, filename=filename)

    with get_db_session() as db:
        stmt = select(Document).where(Document.id == document_id)
        result = db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        job = SyncJob(
            job_type=JobType.DOCUMENT_PROCESS,
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
            metadata_={"document_id": document_id, "source": "upload"},
        )
        db.add(job)

        doc.status = DocumentStatus.PROCESSING.value
        doc.expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        if client_ip is not None and not doc.client_ip:
            doc.client_ip = client_ip
        db.commit()

        try:
            db.add(
                ProcessingLog(
                    document_id=doc.id,
                    job_id=job.id,
                    level=LogLevel.INFO,
                    message=f"Starting ingestion: {filename}",
                )
            )
            db.commit()

            content = base64.b64decode(file_content_b64)

            db.add(
                ProcessingLog(
                    document_id=doc.id,
                    job_id=job.id,
                    level=LogLevel.INFO,
                    message=f"Decoded file content: {len(content)} bytes",
                )
            )
            db.commit()

            indexer = PageLevelIndexer(
                openrouter_api_key=wsettings.openrouter_api_key,
                openrouter_model=wsettings.openrouter_model,
            )

            db.add(
                ProcessingLog(
                    document_id=doc.id,
                    job_id=job.id,
                    level=LogLevel.INFO,
                    message="Parsing with VLM and indexing to OpenSearch...",
                )
            )
            db.commit()

            # The indexer's API is async; run it inside a fresh loop for this
            # synchronous worker actor body.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                indexing_result = loop.run_until_complete(
                    indexer.index_document(
                        content=content,
                        filename=filename,
                        document_id=document_id,
                        delete_existing=True,
                    )
                )
            finally:
                loop.close()

            if not indexing_result.success:
                raise RuntimeError(indexing_result.error or "Indexing failed")

            page_count = indexing_result.page_count

            db.add(
                ProcessingLog(
                    document_id=doc.id,
                    job_id=job.id,
                    level=LogLevel.INFO,
                    message=f"Parsed and indexed: {page_count} pages",
                )
            )
            db.commit()

            doc.status = DocumentStatus.INDEXED.value
            doc.vector_doc_id = document_id
            doc.page_count = page_count
            doc.file_hash = indexing_result.file_hash
            doc.error_message = None

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.metadata_ = {
                "document_id": document_id,
                "page_count": page_count,
                "file_type": indexing_result.file_type,
                "file_hash": indexing_result.file_hash,
                "source": "upload",
            }

            db.add(
                ProcessingLog(
                    document_id=doc.id,
                    job_id=job.id,
                    level=LogLevel.INFO,
                    message=f"Indexing complete: {page_count} pages",
                )
            )
            db.commit()

            logger.info(
                "ingest_completed",
                document_id=document_id,
                filename=filename,
                page_count=page_count,
            )

            return {
                "document_id": document_id,
                "status": "indexed",
                "page_count": page_count,
            }

        except Exception as e:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(e)[:1000]
            doc.retry_count = (doc.retry_count or 0) + 1
            doc.last_error_at = datetime.now(UTC)

            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(UTC)
            job.error_message = str(e)

            db.add(
                ProcessingLog(
                    document_id=doc.id,
                    job_id=job.id,
                    level=LogLevel.ERROR,
                    message=f"Ingestion failed: {e}",
                    details={"exception_type": type(e).__name__},
                )
            )
            db.commit()

            logger.error(
                "ingest_failed",
                document_id=document_id,
                error=str(e),
                exception_type=type(e).__name__,
            )
            raise
