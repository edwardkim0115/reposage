from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx


@dataclass(slots=True)
class GitHubRepoRef:
    owner: str
    repo: str


@dataclass(slots=True)
class GitHubRepoMetadata:
    default_branch: str
    archive_url: str


def validate_github_url(url: str) -> GitHubRepoRef:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError("Only public GitHub repository URLs are supported.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must point to a repository.")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    return GitHubRepoRef(owner=owner, repo=repo)


def _headers(github_token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoSage",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    return headers


def fetch_repository_metadata(ref: GitHubRepoRef, github_token: str | None = None) -> GitHubRepoMetadata:
    url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}"
    with httpx.Client(timeout=30.0, headers=_headers(github_token), follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()
    default_branch = payload["default_branch"]
    archive_url = f"https://codeload.github.com/{ref.owner}/{ref.repo}/zip/refs/heads/{default_branch}"
    return GitHubRepoMetadata(default_branch=default_branch, archive_url=archive_url)


def download_archive(metadata: GitHubRepoMetadata, destination: Path, github_token: str | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60.0, headers=_headers(github_token), follow_redirects=True) as client:
        with client.stream("GET", metadata.archive_url) as response:
            response.raise_for_status()
            with destination.open("wb") as file_obj:
                for chunk in response.iter_bytes():
                    file_obj.write(chunk)
    return destination

