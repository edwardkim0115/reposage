from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from reposage.config import get_settings
from reposage.enums import JobStatus, ProjectStatus, SourceType
from reposage.models import ChatSession, CodeChunk, IndexJob, Project, RepositoryFile
from reposage.repository.github import validate_github_url
from reposage.schemas import IndexJobRead, ProjectDetail, ProjectRead


def list_projects(session: Session) -> list[Project]:
    statement = select(Project).order_by(Project.updated_at.desc())
    return list(session.scalars(statement).all())


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def get_project_detail(session: Session, project_id: str) -> ProjectDetail | None:
    project = get_project(session, project_id)
    if project is None:
        return None
    file_count = session.scalar(select(func.count()).select_from(RepositoryFile).where(RepositoryFile.project_id == project_id)) or 0
    chunk_count = session.scalar(select(func.count()).select_from(CodeChunk).where(CodeChunk.project_id == project_id)) or 0
    latest_job = session.scalar(
        select(IndexJob).where(IndexJob.project_id == project_id).order_by(IndexJob.created_at.desc()).limit(1)
    )
    return ProjectDetail(
        **ProjectRead.model_validate(project).model_dump(),
        file_count=int(file_count),
        chunk_count=int(chunk_count),
        latest_job=IndexJobRead.model_validate(latest_job) if latest_job else None,
    )


def create_project(session: Session, name: str) -> Project:
    project = Project(name=name.strip(), source_type=None, status=ProjectStatus.CREATED)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def create_github_project(session: Session, *, name: str, source_url: str) -> tuple[Project, IndexJob]:
    validate_github_url(source_url)
    project = Project(
        name=name.strip(),
        source_type=SourceType.GITHUB,
        source_url=str(source_url),
        status=ProjectStatus.QUEUED,
    )
    session.add(project)
    session.flush()
    job = IndexJob(project_id=project.id, status=JobStatus.QUEUED, summary={"stage": "queued"})
    session.add(job)
    session.commit()
    session.refresh(project)
    session.refresh(job)
    return project, job


def create_zip_project(session: Session, *, name: str, filename: str, payload: bytes) -> tuple[Project, IndexJob]:
    if not filename.lower().endswith(".zip"):
        raise ValueError("Only ZIP uploads are supported.")

    settings = get_settings()
    project = Project(name=name.strip(), source_type=SourceType.ZIP, status=ProjectStatus.QUEUED)
    session.add(project)
    session.flush()

    upload_dir = settings.uploads_dir / str(project.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    archive_path = upload_dir / f"{uuid4()}.zip"
    archive_path.write_bytes(payload)
    project.source_archive_path = str(archive_path)

    job = IndexJob(project_id=project.id, status=JobStatus.QUEUED, summary={"stage": "queued"})
    session.add(job)
    session.commit()
    session.refresh(project)
    session.refresh(job)
    return project, job


def reindex_project(session: Session, project: Project) -> IndexJob:
    project.status = ProjectStatus.QUEUED
    project.error_message = None
    job = IndexJob(project_id=project.id, status=JobStatus.QUEUED, summary={"stage": "queued"})
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def list_project_files(session: Session, project_id: str, search: str | None = None) -> list[RepositoryFile]:
    statement = select(RepositoryFile).where(RepositoryFile.project_id == project_id)
    if search:
        statement = statement.where(func.lower(RepositoryFile.path).like(f"%{search.lower()}%"))
    statement = statement.order_by(RepositoryFile.path.asc())
    return list(session.scalars(statement).all())


def get_project_file(session: Session, project_id: str, file_id: str) -> RepositoryFile | None:
    statement = (
        select(RepositoryFile)
        .options(selectinload(RepositoryFile.chunks))
        .where(RepositoryFile.project_id == project_id, RepositoryFile.id == file_id)
    )
    return session.scalar(statement)


def list_project_chunks(session: Session, project_id: str, file_id: str | None = None) -> list[CodeChunk]:
    statement = select(CodeChunk).where(CodeChunk.project_id == project_id)
    if file_id:
        statement = statement.where(CodeChunk.repository_file_id == file_id)
    statement = statement.order_by(CodeChunk.path.asc(), CodeChunk.chunk_index.asc())
    return list(session.scalars(statement).all())


def list_project_jobs(session: Session, project_id: str) -> list[IndexJob]:
    statement = select(IndexJob).where(IndexJob.project_id == project_id).order_by(IndexJob.created_at.desc())
    return list(session.scalars(statement).all())


def get_job(session: Session, job_id: str) -> IndexJob | None:
    return session.get(IndexJob, job_id)


def list_chat_sessions(session: Session, project_id: str) -> list[ChatSession]:
    statement = select(ChatSession).where(ChatSession.project_id == project_id).order_by(ChatSession.updated_at.desc())
    return list(session.scalars(statement).all())

