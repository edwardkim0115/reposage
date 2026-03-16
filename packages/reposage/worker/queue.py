from __future__ import annotations

import redis
from rq import Queue, Retry

from reposage.config import get_settings


def get_queue() -> Queue:
    settings = get_settings()
    connection = redis.from_url(settings.redis_url)
    return Queue(settings.rq_queue_name, connection=connection, default_timeout=3600)


def enqueue_index_job(index_job_id: str) -> None:
    get_queue().enqueue(
        "reposage.worker.tasks.run_index_job",
        index_job_id,
        retry=Retry(max=2, interval=[10, 30]),
    )

