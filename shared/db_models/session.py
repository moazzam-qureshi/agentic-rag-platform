"""ChatSession + Message — conversation memory for the RAG agent."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_models.base import Base, TimestampMixin, UUIDMixin


class ChatSession(Base, UUIDMixin, TimestampMixin):
    """A chat session — one conversation thread with the agent."""

    __tablename__ = "chat_sessions"

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Guardrail attribution — IP that started this session.
    client_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title={self.title})>"


class Message(Base, UUIDMixin, TimestampMixin):
    """A single message within a chat session."""

    __tablename__ = "messages"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # user | assistant | system | tool
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # For assistant messages that invoked tools — captured so the trace panel
    # can replay query translation, hybrid search hits, etc.
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content={preview})>"
