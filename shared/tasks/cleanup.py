"""Dramatiq actor that purges expired demo data (24h TTL).

Two sweeps, both keyed off a 24-hour TTL:
1. Documents whose `expires_at < now()` — remove their OpenSearch pages,
   mark the row DELETED.
2. ChatSessions older than 24h — hard-delete the session row, which
   cascades to messages.

Runs on a schedule via the `scheduler` service (APScheduler → enqueue
→ this actor).
"""

from datetime import UTC, datetime, timedelta

import dramatiq
import structlog
from sqlalchemy import delete, select

from shared.db_models import ChatSession, Document, DocumentStatus

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
    sessions_deleted = 0

    store = get_page_store()

    with get_db_session() as db:
        # === 1. Documents past their explicit expires_at ===
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

        # === 2. Chat sessions older than 24h ===
        # Hard-delete the session row; FK ON DELETE CASCADE on Message.session_id
        # removes the conversation contents.
        chat_cutoff = now - timedelta(hours=24)
        del_stmt = delete(ChatSession).where(ChatSession.created_at < chat_cutoff)
        del_result = db.execute(del_stmt)
        sessions_deleted = del_result.rowcount or 0
        db.commit()

    logger.info(
        "cleanup_complete",
        docs_marked_deleted=docs_marked_deleted,
        pages_deleted_total=pages_deleted_total,
        sessions_deleted=sessions_deleted,
    )

    return {
        "docs_marked_deleted": docs_marked_deleted,
        "pages_deleted_total": pages_deleted_total,
        "sessions_deleted": sessions_deleted,
    }
