from __future__ import annotations

from pathlib import PurePosixPath

from reposage.repository.language import detect_language, normalize_repo_path

IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".turbo",
    ".cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    "vendor",
    "coverage",
    "tmp",
    "temp",
}

IGNORED_FILE_NAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "cargo.lock",
    "composer.lock",
}

IGNORED_BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".mp3",
    ".mp4",
    ".wav",
    ".mov",
    ".avi",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}


def should_ignore_path(path: str) -> tuple[bool, str | None]:
    normalized = normalize_repo_path(path)
    path_obj = PurePosixPath(normalized)

    if any(part in IGNORED_DIR_NAMES for part in path_obj.parts[:-1]):
        return True, "ignored_directory"

    if path_obj.name.lower() in IGNORED_FILE_NAMES:
        return True, "ignored_lockfile"

    if path_obj.suffix.lower() in IGNORED_BINARY_EXTENSIONS:
        return True, "ignored_binary_extension"

    if normalized.startswith("../") or normalized == "..":
        return True, "path_traversal"

    return False, None


def is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data:
        return True
    text_chars = sum(1 for byte in data[:4096] if 9 <= byte <= 13 or 32 <= byte <= 126)
    ratio = text_chars / min(len(data), 4096)
    return ratio < 0.75


def looks_minified(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    if len(lines) <= 2 and len(text) > 4000 and any(len(line) > 2000 for line in lines):
        return True
    if len(lines) < 5:
        return False
    average_length = sum(len(line) for line in lines) / len(lines)
    return average_length > 280 and any(len(line) > 500 for line in lines)


def is_supported_candidate(path: str, text: str) -> bool:
    if detect_language(path):
        return True
    return path.endswith(".md") or path.endswith(".txt") or not looks_minified(text)
