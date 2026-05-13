"""Dramatiq actors shared between the API (sender) and worker (runner).

Importing this package as a side-effect registers all actors on the broker.
Both the API (send side) and the worker (run side) must import `shared.tasks`
*after* their own broker module sets the broker.
"""

from shared.tasks.cleanup import cleanup_expired_documents
from shared.tasks.ingest_upload import ingest_uploaded_document

__all__ = [
    "ingest_uploaded_document",
    "cleanup_expired_documents",
]
