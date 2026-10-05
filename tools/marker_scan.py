#!/usr/bin/env python3
"""Scan tracked text files for unresolved development markers.

This intentionally ignores generated build outputs and binary artifacts so the
signal stays actionable for repository validation checks.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

DEFAULT_MARKERS = ("TODO", "FIXME", "XXX", "HACK", "NotImplemented")
SKIP_PARTS = {".pio", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv", "node_modules"}
BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".a", ".o", ".pyc"}


def tracked_files(repo_root: Path) -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], cwd=repo_root, text=True)
    return [repo_root / line for line in output.splitlines()]


def is_scannable_text(path: Path, repo_root: Path) -> bool:
    relative = path.relative_to(repo_root)
    if any(part in SKIP_PARTS for part in relative.parts):
        return False
    if path.suffix.lower() in BINARY_SUFFIXES:
        return False
    try:
        chunk = path.read_bytes()
    except FileNotFoundError:
        return False
    return b"\0" not in chunk


def scan_markers(repo_root: Path, markers: tuple[str, ...] = DEFAULT_MARKERS) -> list[str]:
    hits: list[str] = []
    for path in tracked_files(repo_root):
        if not is_scannable_text(path, repo_root):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(repo_root)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if relative == Path("tools/marker_scan.py") and "DEFAULT_MARKERS" in line:
                continue
            if any(marker in line for marker in markers):
                hits.append(f"{relative}:{line_number}:{line.strip()}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan tracked text files for unresolved development markers.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    hits = scan_markers(repo_root)
    if hits:
        print("\n".join(hits))
        return 1
    print("tracked text marker scan clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
