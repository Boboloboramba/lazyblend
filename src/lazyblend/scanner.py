"""Scan directories for .blend files."""

import os
from pathlib import Path

from lazyblend.blend_parser import BlendInfo, parse_blend_header


def scan_for_blends(
    scan_dirs: list[str],
    show_hidden: bool = False,
    max_depth: int = 5,
) -> list[BlendInfo]:
    """Recursively scan directories for .blend files.

    Args:
        scan_dirs: List of directory paths to scan.
        show_hidden: Whether to include hidden directories/files.
        max_depth: Maximum recursion depth.

    Returns:
        List of BlendInfo objects for found blend files.
    """
    results = []
    seen = set()

    for scan_dir in scan_dirs:
        dir_path = Path(scan_dir)
        if not dir_path.exists() or not dir_path.is_dir():
            continue

        _scan_recursive(dir_path, results, seen, show_hidden, max_depth, 0)

    return sorted(results, key=lambda x: x.path)


def _scan_recursive(
    dir_path: Path,
    results: list[BlendInfo],
    seen: set[str],
    show_hidden: bool,
    max_depth: int,
    current_depth: int,
) -> None:
    if current_depth > max_depth:
        return

    try:
        entries = list(dir_path.iterdir())
    except (PermissionError, OSError):
        return

    for entry in entries:
        if entry.name.startswith(".") and not show_hidden:
            continue

        if entry.is_file() and entry.suffix.lower() == ".blend":
            resolved = str(entry.resolve())
            if resolved not in seen:
                seen.add(resolved)
                results.append(parse_blend_header(resolved))

        elif entry.is_dir() and not entry.is_symlink():
            if entry.name.startswith(".") and not show_hidden:
                continue
            _scan_recursive(entry, results, seen, show_hidden, max_depth, current_depth + 1)


def find_blend_files_in_directory(directory: str) -> list[BlendInfo]:
    """Find blend files in a single directory (non-recursive)."""
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    results = []
    try:
        for entry in dir_path.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".blend":
                results.append(parse_blend_header(str(entry)))
    except (PermissionError, OSError):
        pass

    return sorted(results, key=lambda x: x.path)
