from __future__ import annotations

import redis
from rq import Connection, Worker

from reposage.config import get_settings
from reposage.logging import configure_logging

configure_logging()
settings = get_settings()


def main() -> None:
    connection = redis.from_url(settings.redis_url)
    with Connection(connection):
        worker = Worker([settings.rq_queue_name])
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()

