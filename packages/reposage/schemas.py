from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be blank.")
        return value


class GithubProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be blank.")
        return value


class CitationRead(BaseModel):
    chunk_id: UUID
    file_id: UUID
    path: str
    chunk_type: str
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    preview: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: str | None
    source_url: str | None
    default_branch: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    last_indexed_at: datetime | None


class ProjectDetail(ProjectRead):
    file_count: int
    chunk_count: int
    latest_job: "IndexJobRead | None" = None


class RepositoryFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    path: str
    language: str | None
    file_size: int
    checksum: str
    is_supported: bool
    summary: str | None
    created_at: datetime


class CodeChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_file_id: UUID
    path: str
    language: str | None
    chunk_index: int
    chunk_type: str
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    content: str
    chunk_metadata: dict[str, Any]
    created_at: datetime


class RepositoryFileDetail(RepositoryFileRead):
    content_text: str | None
    chunks: list[CodeChunkRead]


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be blank.")
        return value


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_session_id: UUID
    role: str
    content: str
    citations: list[CitationRead] | None
    created_at: datetime


class ChatReply(BaseModel):
    session: ChatSessionRead
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    suggested_follow_ups: list[str] = Field(default_factory=list)


class IndexJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    summary: dict[str, Any] | None
    error_message: str | None
    created_at: datetime


class HealthRead(BaseModel):
    status: str


ProjectDetail.model_rebuild()
