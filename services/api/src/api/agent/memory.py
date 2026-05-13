"""Postgres-backed session memory for the RAG agent.

Loads conversation history into LangChain `BaseMessage` objects and writes
new messages back to the `messages` table. The agent itself sees a flat
list of messages; persistence concerns live here.
"""

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db_models import ChatSession, Message

logger = structlog.get_logger(__name__)


class PostgresMemory:
    """Conversation memory tied to a single ChatSession."""

    def __init__(self, db: AsyncSession, session_id: str):
        self.db = db
        self.session_id = session_id

    async def get_messages(self) -> list[BaseMessage]:
        """Load the conversation history as LangChain messages."""
        stmt = (
            select(Message)
            .where(Message.session_id == self.session_id)
            .order_by(Message.created_at)
        )

        result = await self.db.execute(stmt)
        db_messages = result.scalars().all()

        messages: list[BaseMessage] = []
        for msg in db_messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                messages.append(SystemMessage(content=msg.content))
            # tool messages: skipped here; the retrieval trace is captured
            # separately in Message.tool_calls for the UI side-panel.

        logger.debug(
            "messages_loaded",
            session_id=self.session_id,
            count=len(messages),
        )

        return messages

    async def add_message(
        self,
        role: str,
        content: str,
        tool_calls: dict | None = None,
    ) -> Message:
        """Append a message to the session."""
        message = Message(
            session_id=self.session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )
        self.db.add(message)
        await self.db.flush()

        logger.debug("message_added", session_id=self.session_id, role=role)

        return message

    async def get_or_create_session(
        self,
        client_ip: str | None = None,
    ) -> ChatSession:
        """Get the existing session, or create it idempotently.

        Uses ON CONFLICT DO NOTHING so concurrent first-requests are safe.
        """
        values: dict = {"id": self.session_id, "metadata_": {}}
        if client_ip is not None:
            values["client_ip"] = client_ip

        stmt = insert(ChatSession).values(**values).on_conflict_do_nothing(index_elements=["id"])
        await self.db.execute(stmt)
        await self.db.flush()

        stmt = select(ChatSession).where(ChatSession.id == self.session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one()

        logger.debug("session_get_or_create", session_id=self.session_id)

        return session

    async def update_session_title(self, title: str) -> None:
        """Set the session title (typically from the first user message)."""
        stmt = select(ChatSession).where(ChatSession.id == self.session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session and not session.title:
            session.title = title[:255]
            await self.db.flush()
