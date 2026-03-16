from __future__ import annotations

import zipfile
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from reposage.enums import JobStatus, ProjectStatus, SourceType
from reposage.models import IndexJob, Project
from reposage.services.indexing import run_index_job


def test_run_index_job_from_uploaded_zip(db_session, monkeypatch, tmp_path: Path) -> None:
    archive_path = tmp_path / "repo.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("sample-repo/src/app.py", "def login():\n    return True\n")
        archive.writestr("sample-repo/node_modules/ignored.js", "console.log('skip')")

    project = Project(
        name="Zip repo",
        source_type=SourceType.ZIP,
        source_archive_path=str(archive_path),
        status=ProjectStatus.QUEUED,
    )
    db_session.add(project)
    db_session.flush()
    job = IndexJob(project_id=project.id, status=JobStatus.QUEUED, summary={"stage": "queued"})
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        "reposage.services.indexing.embed_texts",
        lambda texts: [[0.0, 0.0, 0.0] for _ in texts],
    )
    monkeypatch.setattr(
        "reposage.services.indexing.SessionLocal",
        sessionmaker(bind=db_session.bind, autoflush=False, autocommit=False, expire_on_commit=False),
    )

    run_index_job(str(job.id))

    db_session.expire_all()
    refreshed_project = db_session.get(Project, project.id)
    refreshed_job = db_session.get(IndexJob, job.id)
    assert refreshed_project is not None
    assert refreshed_job is not None
    assert refreshed_project.status == ProjectStatus.READY
    assert refreshed_job.status == JobStatus.READY
    assert refreshed_job.summary["files_indexed"] == 1
    assert refreshed_job.summary["chunks_created"] >= 1
