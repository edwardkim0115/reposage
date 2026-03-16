from __future__ import annotations

import zipfile
from pathlib import Path

from reposage.repository.chunking import fallback_window_chunks
from reposage.repository.filters import is_probably_binary, looks_minified, should_ignore_path
from reposage.repository.language import detect_language, normalize_repo_path
from reposage.repository.zip_utils import safe_extract_zip


def test_should_ignore_paths_and_detect_binary() -> None:
    assert should_ignore_path("node_modules/react/index.js") == (True, "ignored_directory")
    assert should_ignore_path("package-lock.json") == (True, "ignored_lockfile")
    assert should_ignore_path("src/main.py") == (False, None)
    assert is_probably_binary(b"\x00\x01\x02") is True
    assert is_probably_binary(b"print('hello')\n") is False


def test_language_detection_and_normalization() -> None:
    assert normalize_repo_path(r"src\api\main.py") == "src/api/main.py"
    assert detect_language("Dockerfile") == "docker"
    assert detect_language("src/page.tsx") == "tsx"
    assert detect_language("README.md") == "markdown"
    assert detect_language("assets/logo.png") is None


def test_fallback_chunking_preserves_ranges() -> None:
    content = "\n".join(f"line {index}" for index in range(1, 61))
    chunks = fallback_window_chunks(
        "notes.txt",
        "text",
        content,
        max_chars=80,
        overlap_lines=3,
    )
    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line is not None
    assert chunks[1].start_line is not None
    assert chunks[1].start_line <= chunks[0].end_line


def test_safe_extract_zip_blocks_zip_slip(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../evil.py", "boom")

    destination = tmp_path / "out"
    try:
        safe_extract_zip(
            archive_path,
            destination,
            max_total_size_bytes=1024 * 1024,
            max_total_files=10,
        )
    except ValueError as exc:
        assert "unsafe path" in str(exc).lower()
    else:
        raise AssertionError("Expected unsafe ZIP extraction to raise ValueError.")


def test_minified_detection() -> None:
    minified = "var a=1;" * 700
    assert looks_minified(minified) is True
    multiline_minified = "\n".join(["const x=1;" * 80 for _ in range(8)])
    assert looks_minified(multiline_minified) is True
