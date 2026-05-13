"""ProcessingLog — append-only log of events during document processing."""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db_models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.db_models.document import Document


class LogLevel(str, Enum):
    """Severity of a processing event."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProcessingLog(Base, UUIDMixin, TimestampMixin):
    """A single processing event tied to a document and/or job."""

    __tablename__ = "processing_logs"

    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("sync_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    level: Mapped[LogLevel] = mapped_column(
        default=LogLevel.INFO,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document: Mapped["Document | None"] = relationship(back_populates="processing_logs")

    def __repr__(self) -> str:
        preview = self.message[:50]
        return f"<ProcessingLog(id={self.id}, level={self.level}, message={preview})>"
