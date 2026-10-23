"""Run local quality gates; integration remains explicit."""

import subprocess
import sys

for command in (
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
    ["mypy", "src"],
    ["pytest", "tests/unit"],
):
    result = subprocess.run([sys.executable, "-m", *command], check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
