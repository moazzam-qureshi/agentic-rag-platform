"""Dramatiq Redis broker for the API service.

The API enqueues jobs (e.g. VLM ingestion of an uploaded document) here.
The worker process — see services/worker/ — pulls and executes them.
"""

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from api.config import settings

redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)
