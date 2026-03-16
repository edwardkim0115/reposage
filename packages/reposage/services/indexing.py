from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from reposage.config import Settings, get_settings
from reposage.db import SessionLocal
from reposage.enums import JobStatus, ProjectStatus, SourceType
from reposage.models import CodeChunk, IndexJob, Project, RepositoryFile
from reposage.repository.chunking import analyze_file
from reposage.repository.filters import is_probably_binary, looks_minified, should_ignore_path
from reposage.repository.github import download_archive, fetch_repository_metadata, validate_github_url
from reposage.repository.language import detect_language, normalize_repo_path
from reposage.repository.zip_utils import safe_extract_zip
from reposage.services.llm import embed_texts

logger = logging.getLogger(__name__)


def run_index_job(index_job_id: str) -> None:
    settings = get_settings()
    session = SessionLocal()
    try:
        job = session.get(IndexJob, index_job_id)
        if job is None:
            raise ValueError(f"Index job {index_job_id} was not found.")
        project = session.get(Project, job.project_id)
        if project is None:
            raise ValueError(f"Project {job.project_id} was not found.")

        _mark_job(session, project, job, status=JobStatus.INDEXING, stage="ingestion")
        workspace = settings.temp_dir / str(project.id) / str(job.id)
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        source_root = _prepare_source_workspace(project, workspace, settings)
        created_chunks, summary = _index_workspace(session, project, source_root, settings)

        _mark_job(
            session,
            project,
            job,
            status=JobStatus.EMBEDDING,
            stage="embedding",
            extra_summary=summary,
        )
        if created_chunks:
            _embed_chunks(session, created_chunks)

        project.status = ProjectStatus.READY
        project.error_message = None
        project.last_indexed_at = datetime.utcnow()
        job.status = JobStatus.READY
        job.finished_at = datetime.utcnow()
        job.summary = {**(job.summary or {}), **summary, "stage": "ready"}
        session.commit()
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception as exc:
        logger.exception("Indexing failed for job %s", index_job_id)
        job = session.get(IndexJob, index_job_id)
        if job is not None:
            project = session.get(Project, job.project_id)
            job.status = JobStatus.FAILED
            job.finished_at = datetime.utcnow()
            job.error_message = str(exc)
            job.summary = {**(job.summary or {}), "stage": "failed"}
            if project is not None:
                project.status = ProjectStatus.FAILED
                project.error_message = str(exc)
            session.commit()
        raise
    finally:
        session.close()


def _mark_job(
    session: Session,
    project: Project,
    job: IndexJob,
    *,
    status: str,
    stage: str,
    extra_summary: dict | None = None,
) -> None:
    project.status = ProjectStatus.INDEXING if status != JobStatus.READY else ProjectStatus.READY
    job.status = status
    job.started_at = job.started_at or datetime.utcnow()
    job.summary = {**(job.summary or {}), **(extra_summary or {}), "stage": stage}
    session.commit()


def _prepare_source_workspace(project: Project, workspace: Path, settings: Settings) -> Path:
    source_root = workspace / "repo"
    source_root.mkdir(parents=True, exist_ok=True)

    if project.source_type == SourceType.GITHUB:
        if not project.source_url:
            raise ValueError("GitHub source URL is missing.")
        ref = validate_github_url(project.source_url)
        token = settings.github_token.get_secret_value() if settings.github_token else None
        metadata = fetch_repository_metadata(ref, token)
        archive_path = workspace / "github-repo.zip"
        download_archive(metadata, archive_path, token)
        project.default_branch = metadata.default_branch
        safe_extract_zip(
            archive_path,
            source_root,
            max_total_size_bytes=settings.max_repository_size_bytes,
            max_total_files=settings.max_total_files,
            strip_top_level=True,
        )
        return source_root

    if project.source_type == SourceType.ZIP:
        if not project.source_archive_path:
            raise ValueError("Uploaded source archive is missing.")
        archive_path = Path(project.source_archive_path)
        if not archive_path.exists():
            raise ValueError("Uploaded source archive could not be found.")
        safe_extract_zip(
            archive_path,
            source_root,
            max_total_size_bytes=settings.max_repository_size_bytes,
            max_total_files=settings.max_total_files,
            strip_top_level=True,
        )
        return source_root

    raise ValueError("Project does not have a supported source type.")


def _index_workspace(
    session: Session,
    project: Project,
    source_root: Path,
    settings: Settings,
) -> tuple[list[CodeChunk], dict]:
    session.execute(delete(CodeChunk).where(CodeChunk.project_id == project.id))
    session.execute(delete(RepositoryFile).where(RepositoryFile.project_id == project.id))
    session.commit()

    created_chunks: list[CodeChunk] = []
    files_indexed = 0
    supported_files = 0
    skipped_files = 0

    for file_path in sorted(source_root.rglob("*")):
        if not file_path.is_file():
            continue

        relative_path = normalize_repo_path(str(file_path.relative_to(source_root)))
        ignored, reason = should_ignore_path(relative_path)
        if ignored:
            logger.debug("Skipping %s: %s", relative_path, reason)
            skipped_files += 1
            continue

        file_size = file_path.stat().st_size
        if files_indexed >= settings.max_total_files:
            raise ValueError("Repository exceeds the maximum allowed file count.")

        data = file_path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        language = detect_language(relative_path)

        if file_size > settings.max_file_size_bytes:
            repository_file = RepositoryFile(
                project_id=project.id,
                path=relative_path,
                language=language,
                file_size=file_size,
                checksum=checksum,
                is_supported=False,
                summary="Skipped file larger than the configured maximum size.",
            )
            session.add(repository_file)
            files_indexed += 1
            continue

        if is_probably_binary(data):
            repository_file = RepositoryFile(
                project_id=project.id,
                path=relative_path,
                language=language,
                file_size=file_size,
                checksum=checksum,
                is_supported=False,
                summary="Skipped binary file.",
            )
            session.add(repository_file)
            files_indexed += 1
            continue

        text = data.decode("utf-8", errors="ignore")
        supported = language is not None and not looks_minified(text)
        analysis = (
            analyze_file(
                relative_path,
                text,
                max_chars=settings.chunk_max_chars,
                overlap_lines=settings.chunk_overlap_lines,
            )
            if supported
            else None
        )
        repository_file = RepositoryFile(
            project_id=project.id,
            path=relative_path,
            language=language,
            file_size=file_size,
            checksum=checksum,
            is_supported=supported,
            content_text=text if supported else None,
            summary=(analysis.summary if analysis else "Skipped unsupported or minified file."),
        )
        session.add(repository_file)
        session.flush()

        if analysis:
            supported_files += 1
            for chunk_index, chunk in enumerate(analysis.chunks):
                model_chunk = CodeChunk(
                    project_id=project.id,
                    repository_file_id=repository_file.id,
                    path=relative_path,
                    language=analysis.language,
                    chunk_index=chunk_index,
                    chunk_type=chunk.chunk_type,
                    symbol_name=chunk.symbol_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    content=chunk.content,
                    search_text=" ".join(
                        part for part in [relative_path, chunk.symbol_name or "", chunk.content] if part
                    ),
                    chunk_metadata=chunk.metadata,
                )
                session.add(model_chunk)
                created_chunks.append(model_chunk)

        files_indexed += 1

    session.commit()
    return created_chunks, {
        "files_indexed": files_indexed,
        "supported_files": supported_files,
        "chunks_created": len(created_chunks),
        "skipped_files": skipped_files,
    }


def _embed_chunks(session: Session, chunks: list[CodeChunk]) -> None:
    batch_size = 64
    for index in range(0, len(chunks), batch_size):
        batch = chunks[index : index + batch_size]
        embeddings = embed_texts([chunk.content for chunk in batch])
        for chunk, embedding in zip(batch, embeddings, strict=False):
            chunk.embedding = embedding
        session.commit()

