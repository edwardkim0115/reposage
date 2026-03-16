from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from apps.api.app.deps import get_db
from reposage.schemas import CodeChunkRead, RepositoryFileDetail, RepositoryFileRead
from reposage.services.projects import get_project, get_project_file, list_project_chunks, list_project_files

router = APIRouter(tags=["files"])


@router.get("/projects/{project_id}/files", response_model=list[RepositoryFileRead])
def list_files_endpoint(
    project_id: str,
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RepositoryFileRead]:
    if get_project(db, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return [RepositoryFileRead.model_validate(file) for file in list_project_files(db, project_id, search)]


@router.get("/projects/{project_id}/files/{file_id}", response_model=RepositoryFileDetail)
def get_file_endpoint(project_id: str, file_id: str, db: Session = Depends(get_db)) -> RepositoryFileDetail:
    file = get_project_file(db, project_id, file_id)
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return RepositoryFileDetail.model_validate(file)


@router.get("/projects/{project_id}/chunks", response_model=list[CodeChunkRead])
def list_chunks_endpoint(
    project_id: str,
    file_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CodeChunkRead]:
    if get_project(db, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return [CodeChunkRead.model_validate(chunk) for chunk in list_project_chunks(db, project_id, file_id)]

