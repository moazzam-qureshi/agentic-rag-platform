"""Dramatiq actor that purges expired uploads (24h TTL).

Removes Document rows and their OpenSearch pages whose `expires_at` is in
the past. Runs on a schedule via the `scheduler` service (APScheduler →
enqueue → this actor).
"""

from datetime import UTC, datetime

import dramatiq
import structlog
from sqlalchemy import select

from shared.db_models import Document, DocumentStatus

logger = structlog.get_logger(__name__)


@dramatiq.actor(
    queue_name="cleanup",
    priority=10,
    max_retries=1,
    time_limit=5 * 60 * 1000,  # 5 min
)
def cleanup_expired_documents() -> dict:
    """Delete documents past their TTL plus their OpenSearch pages.

    Idempotent: safe to run repeatedly. Returns counts for observability.
    """
    # Late imports: worker-side modules.
    # Import the OpenSearch store from the api package — both run-times
    # have it on PYTHONPATH (we install the api source into the worker image
    # too, see services/worker/Dockerfile).
    from api.db.opensearch_store import get_page_store
    from worker.db.session import get_db_session

    now = datetime.now(UTC)
    pages_deleted_total = 0
    docs_marked_deleted = 0

    store = get_page_store()

    with get_db_session() as db:
        stmt = (
            select(Document)
            .where(Document.expires_at.is_not(None))
            .where(Document.expires_at < now)
            .where(Document.status != DocumentStatus.DELETED.value)
        )
        result = db.execute(stmt)
        expired = result.scalars().all()

        for doc in expired:
            try:
                pages_deleted = store.delete_document(doc.id)
                pages_deleted_total += pages_deleted

                doc.status = DocumentStatus.DELETED.value
                docs_marked_deleted += 1
            except Exception as e:
                logger.error(
                    "cleanup_doc_failed",
                    document_id=doc.id,
                    error=str(e),
                )

        db.commit()

    logger.info(
        "cleanup_complete",
        docs_marked_deleted=docs_marked_deleted,
        pages_deleted_total=pages_deleted_total,
    )

    return {
        "docs_marked_deleted": docs_marked_deleted,
        "pages_deleted_total": pages_deleted_total,
    }
