"""GET /sessions/:id — load a chat session and its messages.

Used by the frontend to rehydrate a conversation after page reload.
The session is scoped to the caller's IP — same ownership rule as
documents and jobs.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from shared.db_models import ChatSession, Message
from shared.guardrails.client_ip import get_client_ip

logger = structlog.get_logger(__name__)

router = APIRouter()


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
