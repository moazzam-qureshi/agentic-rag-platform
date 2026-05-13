"""Document model — tracks an uploaded document through its lifecycle."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.db_models.log import ProcessingLog


class DocumentStatus(str, Enum):
    """Lifecycle status of an uploaded document."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class Document(Base, UUIDMixin, TimestampMixin):
    """An uploaded document and its processing state."""

    __tablename__ = "documents"

    # Identity
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # Processing status (stored as plain string to avoid PostgreSQL enum type)
    status: Mapped[str] = mapped_column(
        String(20),
        default=DocumentStatus.PENDING.value,
        nullable=False,
    )

    # Vector store reference (same UUID as id, kept explicit for clarity)
    vector_doc_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Statistics
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Guardrail attribution — the IP that uploaded this doc.
    # Used by the daily cleanup job and per-IP cost ceiling.
    client_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )

    # Flexible metadata storage
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    processing_logs: Mapped[list["ProcessingLog"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_documents_status_updated", "status", "updated_at"),
        Index("ix_documents_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
