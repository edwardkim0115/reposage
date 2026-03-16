from __future__ import annotations

from reposage.logging import configure_logging
from reposage.services.indexing import run_index_job as execute_index_job

configure_logging()


def run_index_job_task(index_job_id: str) -> None:
    execute_index_job(index_job_id)


run_index_job = run_index_job_task
