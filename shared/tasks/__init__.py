"""Dramatiq actors shared between the API (sender) and worker (runner)."""

from shared.tasks.ingest_upload import ingest_uploaded_document

__all__ = ["ingest_uploaded_document"]
