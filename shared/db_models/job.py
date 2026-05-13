"""SyncJob — tracks a background processing job (worker-driven)."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db_models.base import Base, TimestampMixin, UUIDMixin


class JobType(StrEnum):
    """Type of background job."""

    DOCUMENT_PROCESS = "document_process"
    DOCUMENT_DELETE = "document_delete"
    EXPIRY_CLEANUP = "expiry_cleanup"


class JobStatus(StrEnum):
    """Lifecycle status of a job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncJob(Base, UUIDMixin, TimestampMixin):
    """A background processing job, e.g. VLM ingestion of an uploaded doc."""

    __tablename__ = "sync_jobs"

    job_type: Mapped[JobType] = mapped_column(nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        default=JobStatus.PENDING,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SyncJob(id={self.id}, type={self.job_type}, status={self.status})>"
