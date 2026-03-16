from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from apps.api.app.deps import get_db
from reposage.config import get_settings
from reposage.schemas import GithubProjectCreate, IndexJobRead, ProjectCreate, ProjectDetail, ProjectRead
from reposage.services.projects import (
    create_github_project,
    create_project,
    create_zip_project,
    get_project,
    get_project_detail,
    list_projects,
    reindex_project,
)
from reposage.worker.queue import enqueue_index_job

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectRead])
def get_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return [ProjectRead.model_validate(project) for project in list_projects(db)]


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    project = create_project(db, payload.name)
    return ProjectRead.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project_endpoint(project_id: str, db: Session = Depends(get_db)) -> ProjectDetail:
    detail = get_project_detail(db, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return detail


@router.post("/projects/github", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_github_project_endpoint(
    payload: GithubProjectCreate, db: Session = Depends(get_db)
) -> ProjectDetail:
    try:
        project, job = create_github_project(db, name=payload.name, source_url=str(payload.source_url))
        enqueue_index_job(str(job.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    detail = get_project_detail(db, str(project.id))
    assert detail is not None
    return detail


@router.post("/projects/upload-zip", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def upload_zip_project_endpoint(
    name: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
) -> ProjectDetail:
    settings = get_settings()
    payload = file.file.read()
    if len(payload) > settings.max_repository_size_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archive is too large.")
    try:
        project, job = create_zip_project(db, name=name, filename=file.filename or "upload.zip", payload=payload)
        enqueue_index_job(str(job.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    detail = get_project_detail(db, str(project.id))
    assert detail is not None
    return detail


@router.post("/projects/{project_id}/reindex", response_model=IndexJobRead, status_code=status.HTTP_202_ACCEPTED)
def reindex_project_endpoint(project_id: str, db: Session = Depends(get_db)) -> IndexJobRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if not project.source_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no source to re-index.")
    job = reindex_project(db, project)
    enqueue_index_job(str(job.id))
    return IndexJobRead.model_validate(job)

