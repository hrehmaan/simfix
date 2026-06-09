from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FixResult:
    """Result of a dependency fix operation."""

    file_path: Path
    changed: bool
    message: str


def _command_exists(command: str) -> bool:
    """Return True if a command exists on PATH."""
    return shutil.which(command) is not None


def fix_requirements_with_uv(repo_path: str | Path) -> FixResult | None:
    """Resolve and update requirements.txt in place using uv.

    This updates the original requirements.txt file.
    """
    path = Path(repo_path).expanduser().resolve()
    requirements_path = path / "requirements.txt"

    if not requirements_path.exists():
        return None

    if not _command_exists("uv"):
        return FixResult(
            file_path=requirements_path,
            changed=False,
            message=("uv was not found. Install it with: " "python -m pip install uv"),
        )

    old_text = requirements_path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as temporary_directory:
        output_path = Path(temporary_directory) / "requirements.txt"

        result = subprocess.run(
            [
                "uv",
                "pip",
                "compile",
                str(requirements_path),
                "--upgrade",
                "-o",
                str(output_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return FixResult(
                file_path=requirements_path,
                changed=False,
                message=result.stderr.strip() or "uv failed to resolve requirements.",
            )

        new_text = output_path.read_text(encoding="utf-8")

    changed = old_text != new_text

    if changed:
        requirements_path.write_text(new_text, encoding="utf-8")

    return FixResult(
        file_path=requirements_path,
        changed=changed,
        message="requirements.txt resolved successfully with uv.",
    )
