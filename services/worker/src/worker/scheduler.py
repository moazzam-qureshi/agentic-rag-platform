"""Scheduler process — enqueues periodic Dramatiq jobs.

This is a separate container from the worker. It does no heavy work itself;
it just calls `cleanup_expired_documents.send()` once an hour.
"""

# ruff: noqa: I001, E402  — broker must be imported before actor imports.

import logging
import signal
import sys

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Broker first, then actor import so .send() routes to the right Redis.
from worker import broker  # noqa: F401
from shared.tasks import cleanup_expired_documents

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

logger = structlog.get_logger(__name__)


def main() -> None:
    scheduler = BlockingScheduler()

    # Hourly: scan for expired uploads and purge their DB + OpenSearch state.
    scheduler.add_job(
        cleanup_expired_documents.send,
        IntervalTrigger(hours=1),
        id="cleanup_expired_documents",
        name="Purge expired uploads (24h TTL)",
        replace_existing=True,
    )

    def shutdown(signum, frame):
        logger.info("scheduler_stopping")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Run one cleanup pass at startup so containers coming up after downtime
    # don't carry stale data forward.
    try:
        cleanup_expired_documents.send()
        logger.info("initial_cleanup_enqueued")
    except Exception as e:
        logger.error("initial_cleanup_failed", error=str(e))

    logger.info("scheduler_started", interval="hourly")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler_stopped")


if __name__ == "__main__":
    main()
