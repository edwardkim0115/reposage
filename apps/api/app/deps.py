from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from reposage.db import get_db_session


def get_db() -> Iterator[Session]:
    yield from get_db_session()

