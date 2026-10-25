"""Canonical identity of actual009 code, migrations and runner, never local secrets."""

import hashlib
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]


def source_identity() -> dict[str, Any]:
    directories = ("src", "scripts", "migrations/scale")
    files = sorted(
        [
            *(p for directory in directories for p in (ROOT / directory).rglob("*.py")),
            ROOT / "pyproject.toml",
            ROOT / "uv.lock",
        ]
    )
    digest = hashlib.sha256()
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError("Unsafe009source path")
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0")
        digest.update(path.read_text(encoding="utf-8").encode() + b"\0")
    dirty = subprocess.check_output(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *directories,
            "pyproject.toml",
            "uv.lock",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    return {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "sha256": digest.hexdigest(),
        "sources_dirty": bool(dirty),
        "files": len(files),
    }
