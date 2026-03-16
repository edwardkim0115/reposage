from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.deps import get_db
from reposage.schemas import IndexJobRead
from reposage.services.projects import get_job, get_project, list_project_jobs

router = APIRouter(tags=["jobs"])


@router.get("/projects/{project_id}/jobs", response_model=list[IndexJobRead])
def list_project_jobs_endpoint(project_id: str, db: Session = Depends(get_db)) -> list[IndexJobRead]:
    if get_project(db, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return [IndexJobRead.model_validate(job) for job in list_project_jobs(db, project_id)]


@router.get("/jobs/{job_id}", response_model=IndexJobRead)
def get_job_endpoint(job_id: str, db: Session = Depends(get_db)) -> IndexJobRead:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return IndexJobRead.model_validate(job)

