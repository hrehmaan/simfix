from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from simfix.conda_fixer import fix_conda_environment_file
from simfix.cuda_docker import create_cuda_dockerfile
from simfix.ros_docker import create_ros_dockerfile


@dataclass(frozen=True)
class CombinedFixResult:
    """Combined result of all fixers."""

    messages: list[str]
    changed_files: list[Path]


def _command_exists(command: str) -> bool:
    """Return True if a command exists on PATH."""
    return shutil.which(command) is not None


@dataclass(frozen=True)
class FixResult:
    """Result of a dependency fix operation."""

    file_path: Path
    changed: bool
    message: str


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


def fix_repo(repo_path: str | Path) -> CombinedFixResult:
    """Run all supported fixers for a repository."""
    messages: list[str] = []
    changed_files: list[Path] = []

    requirements_result = fix_requirements_with_uv(repo_path)

    if requirements_result is not None:
        messages.append(requirements_result.message)

        if requirements_result.changed:
            changed_files.append(requirements_result.file_path)

    conda_result = fix_conda_environment_file(repo_path)

    if conda_result is not None:
        messages.append(conda_result.message)

        if conda_result.changed:
            changed_files.append(conda_result.file_path)

    cuda_result = create_cuda_dockerfile(repo_path)

    if cuda_result is not None:
        messages.append(cuda_result.message)

        if cuda_result.changed:
            changed_files.append(cuda_result.file_path)

    ros_result = create_ros_dockerfile(repo_path)

    if ros_result is not None:
        messages.append(ros_result.message)

        if ros_result.changed:
            changed_files.append(ros_result.file_path)

    if not messages:
        messages.append("No supported dependency files found to fix yet.")

    return CombinedFixResult(
        messages=messages,
        changed_files=changed_files,
    )
