"""Chat session endpoints — scoped by caller IP.

GET /sessions          → list the caller's sessions for the sidebar history
GET /sessions/:id      → load one session + its messages (rehydration)
DELETE /sessions/:id   → user removes a conversation
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from shared.db_models import ChatSession, Message
from shared.guardrails.client_ip import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/sessions")
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List the caller's chat sessions, newest first.

    Each entry has the metadata the sidebar needs — id, title,
    created_at, updated_at, and message_count for a subtle hint.
    Returns at most 100 (defensive cap; the 24h cleanup keeps the
    real number much lower).
    """
    client_ip = get_client_ip(request)

    # Subquery counting messages per session, joined back so we get them
    # in one round-trip instead of N+1.
    msg_count_subq = (
        select(
            Message.session_id.label("sid"),
            func.count(Message.id).label("msg_count"),
        )
        .group_by(Message.session_id)
        .subquery()
    )

    stmt = (
        select(ChatSession, func.coalesce(msg_count_subq.c.msg_count, 0))
        .outerjoin(msg_count_subq, msg_count_subq.c.sid == ChatSession.id)
        .where(ChatSession.client_ip == client_ip)
        .order_by(ChatSession.updated_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "message_count": int(count),
            }
            for s, count in rows
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a chat session and its messages, oldest first.

    404 if the session doesn't exist or belongs to another caller.
    """
    client_ip = get_client_ip(request)

    stmt = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Same ownership rule as /documents — sessions created without an IP
    # (e.g. legacy data) are treated as not-yours. New sessions always
    # have client_ip set by the chat route.
    if session.client_ip != client_ip:
        raise HTTPException(status_code=404, detail="Session not found.")

    msg_stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    msg_result = await db.execute(msg_stmt)
    msgs = msg_result.scalars().all()

    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
            # Skip system / tool messages — only user/assistant turns are
            # meaningful for UI rehydration.
            if m.role in ("user", "assistant")
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Hard-delete a session (cascades to its messages via FK).

    404 on cross-IP / unknown — same ownership rule as the GET handlers.
    """
    client_ip = get_client_ip(request)

    stmt = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session or session.client_ip != client_ip:
        raise HTTPException(status_code=404, detail="Session not found.")

    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.flush()

    logger.info("session_deleted", session_id=session_id, client_ip=client_ip)

    return {"session_id": session_id, "deleted": True}
