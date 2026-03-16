from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    GITHUB = "github"
    ZIP = "zip"


class ProjectStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class JobStatus(StrEnum):
    QUEUED = "queued"
    INDEXING = "indexing"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"

