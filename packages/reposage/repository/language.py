from __future__ import annotations

from pathlib import PurePosixPath

FILE_NAME_LANGUAGE_MAP = {
    "dockerfile": "docker",
    "makefile": "makefile",
    ".env": "dotenv",
    ".env.example": "dotenv",
    ".gitignore": "gitignore",
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".txt": "text",
    ".sql": "sql",
    ".sh": "shell",
    ".ini": "ini",
}

SUPPORTED_LANGUAGES = set(EXTENSION_LANGUAGE_MAP.values()) | set(FILE_NAME_LANGUAGE_MAP.values())


def normalize_repo_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip("/")
    return str(PurePosixPath(normalized))


def detect_language(path: str) -> str | None:
    path_obj = PurePosixPath(normalize_repo_path(path))
    if path_obj.name.lower() in FILE_NAME_LANGUAGE_MAP:
        return FILE_NAME_LANGUAGE_MAP[path_obj.name.lower()]
    return EXTENSION_LANGUAGE_MAP.get(path_obj.suffix.lower())


def is_supported_text_file(path: str) -> bool:
    return detect_language(path) is not None

