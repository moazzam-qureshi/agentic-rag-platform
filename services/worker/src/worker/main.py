"""Worker entry-point — imported by `dramatiq worker.main`.

Order matters:
1. worker.broker must run FIRST so dramatiq.set_broker() executes before any
   actor decoration.
2. shared.tasks imports the actor modules, which register against the broker.
"""

import logging
import sys

import structlog

# 1. Set the broker BEFORE importing actors.
from worker import broker  # noqa: F401

# 2. Import actors — this registers them on the broker.
from shared.tasks import (  # noqa: F401, E402
    cleanup_expired_documents,
    ingest_uploaded_document,
)

# 3. Structured logging for the worker.
logging.basicConfig(stream=sys.stdout, format="%(message)s", level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

structlog.get_logger(__name__).info(
    "worker_module_loaded",
    actors=[ingest_uploaded_document.actor_name, cleanup_expired_documents.actor_name],
)
