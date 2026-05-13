"""Synchronous SQLAlchemy session for Dramatiq actor bodies.

Dramatiq actors run in sync workers, so we use the sync driver here even
though the API service runs async. The two share the same DATABASE_URL —
this module strips the asyncpg scheme.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from worker.config import settings

sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(
    sync_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

session_factory = sessionmaker(
    engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context-managed sync session with auto commit/rollback."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
