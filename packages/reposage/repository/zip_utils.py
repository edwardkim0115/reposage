from __future__ import annotations

import shutil
import zipfile
from pathlib import Path, PurePosixPath


def _is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    permissions = info.external_attr >> 16
    return (permissions & 0o170000) == 0o120000


def safe_extract_zip(
    archive_path: Path,
    destination: Path,
    *,
    max_total_size_bytes: int,
    max_total_files: int,
    strip_top_level: bool = False,
) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    extracted_paths: list[Path] = []
    total_size = 0

    with zipfile.ZipFile(archive_path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if len(members) > max_total_files:
            raise ValueError("Archive contains too many files.")

        common_prefix = None
        if strip_top_level and members:
            first_parts = [PurePosixPath(member.filename).parts[0] for member in members if member.filename]
            if first_parts and len(set(first_parts)) == 1:
                common_prefix = first_parts[0]

        for member in members:
            if _is_zip_symlink(member):
                continue

            total_size += member.file_size
            if total_size > max_total_size_bytes:
                raise ValueError("Archive exceeds the maximum allowed extracted size.")

            raw_path = PurePosixPath(member.filename)
            member_parts = raw_path.parts
            if common_prefix and member_parts and member_parts[0] == common_prefix:
                member_parts = member_parts[1:]

            if not member_parts:
                continue

            relative_path = PurePosixPath(*member_parts)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError("Archive contains an unsafe path.")

            output_path = (destination / Path(*relative_path.parts)).resolve()
            destination_resolved = destination.resolve()
            if destination_resolved not in output_path.parents and output_path != destination_resolved:
                raise ValueError("Archive extraction escaped the target directory.")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, output_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            extracted_paths.append(output_path)

    return extracted_paths

