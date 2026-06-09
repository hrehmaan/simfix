from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from simfix.conda_fixer import fix_conda_environment_file
from simfix.cuda_docker import create_cuda_dockerfile
from simfix.docker_runner import create_docker_run_helper
from simfix.git_assets import fix_git_assets
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


def extract_direct_pin_conflict(error_text: str) -> str | None:
    """Extract the directly pinned package causing a uv conflict.

    Example uv message:
    Because urdfpy==0.0.22 depends on networkx==2.2 ...
    And because you require networkx==3.1, ...
    returns: "networkx"
    """
    dependency_match = re.search(
        r"depends on ([A-Za-z0-9_.-]+)==[A-Za-z0-9_.!+-]+",
        error_text,
    )

    if dependency_match is None:
        return None

    dependency_name = dependency_match.group(1).lower()

    required_matches = re.findall(
        r"you require ([A-Za-z0-9_.-]+)==[A-Za-z0-9_.!+-]+",
        error_text,
    )

    for required_name in required_matches:
        if required_name.lower() == dependency_name:
            return required_name

    return None


def remove_direct_requirement_pin(
    requirements_text: str,
    package_name: str,
) -> str:
    """Remove a direct exact-version pin from requirements text."""
    pattern = re.compile(
        rf"^\s*{re.escape(package_name)}\s*==\s*[^\s#]+.*\n?",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    return pattern.sub("", requirements_text)


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
    normalized_text = normalize_pip_requirement_syntax(old_text)

    if normalized_text != old_text:
        requirements_path.write_text(normalized_text, encoding="utf-8")

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
            error_text = result.stderr.strip() or result.stdout.strip()
            conflicting_package = extract_direct_pin_conflict(error_text)

            if conflicting_package is not None:
                current_text = requirements_path.read_text(encoding="utf-8")
                fixed_text = remove_direct_requirement_pin(
                    current_text,
                    conflicting_package,
                )

                if fixed_text != current_text:
                    requirements_path.write_text(fixed_text, encoding="utf-8")

                    retry_result = subprocess.run(
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

                    if retry_result.returncode == 0:
                        new_text = output_path.read_text(encoding="utf-8")
                        requirements_path.write_text(new_text, encoding="utf-8")

                        return FixResult(
                            file_path=requirements_path,
                            changed=True,
                            message=(
                                "requirements.txt conflict repaired by removing "
                                f"the direct {conflicting_package} pin and letting "
                                "uv resolve the compatible version."
                            ),
                        )

                    return FixResult(
                        file_path=requirements_path,
                        changed=True,
                        message=(
                            f"Removed direct {conflicting_package} pin, "
                            "but uv still failed: "
                            + (
                                retry_result.stderr.strip()
                                or retry_result.stdout.strip()
                            )
                        ),
                    )

            return FixResult(
                file_path=requirements_path,
                changed=False,
                message=error_text or "uv failed to resolve requirements.",
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


def fix_pyproject_with_uv(repo_path: str | Path) -> FixResult | None:
    """Resolve pyproject.toml dependencies into requirements.txt using uv.

    This creates requirements.txt only when pyproject.toml exists and
    requirements.txt does not already exist.
    """
    path = Path(repo_path).expanduser().resolve()
    pyproject_path = path / "pyproject.toml"
    requirements_path = path / "requirements.txt"

    if not pyproject_path.exists():
        return None

    if requirements_path.exists():
        return None

    if not _command_exists("uv"):
        return FixResult(
            file_path=requirements_path,
            changed=False,
            message=("uv was not found. Install it with: " "python -m pip install uv"),
        )

    result = subprocess.run(
        [
            "uv",
            "pip",
            "compile",
            str(pyproject_path),
            "--upgrade",
            "-o",
            str(requirements_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return FixResult(
            file_path=requirements_path,
            changed=False,
            message=result.stderr.strip()
            or "uv failed to resolve pyproject.toml dependencies.",
        )

    return FixResult(
        file_path=requirements_path,
        changed=True,
        message="Created requirements.txt from pyproject.toml using uv.",
    )


def normalize_pip_requirement_syntax(text: str) -> str:
    """Normalize simple invalid pip requirement syntax.

    Converts package=version to package==version.
    """
    normalized_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()

        if (
            stripped
            and not stripped.startswith("#")
            and "=" in stripped
            and "==" not in stripped
            and ">=" not in stripped
            and "<=" not in stripped
            and "!=" not in stripped
            and "~=" not in stripped
        ):
            name, version = stripped.split("=", maxsplit=1)
            normalized_lines.append(f"{name.strip()}=={version.strip()}")
        else:
            normalized_lines.append(line)

    return "\n".join(normalized_lines) + "\n"


def fix_repo(repo_path: str | Path) -> CombinedFixResult:
    """Run all supported fixers for a repository."""
    messages: list[str] = []
    changed_files: list[Path] = []

    requirements_result = fix_requirements_with_uv(repo_path)

    if requirements_result is not None:
        messages.append(requirements_result.message)

        if requirements_result.changed:
            changed_files.append(requirements_result.file_path)

    pyproject_result = fix_pyproject_with_uv(repo_path)
    if pyproject_result is not None:
        messages.append(pyproject_result.message)

        if pyproject_result.changed:
            changed_files.append(pyproject_result.file_path)

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

    docker_run_result = create_docker_run_helper(repo_path)
    if docker_run_result is not None:
        messages.append(docker_run_result.message)

        if docker_run_result.changed:
            changed_files.append(docker_run_result.file_path)

    git_assets_result = fix_git_assets(repo_path)
    if git_assets_result is not None:
        messages.append(git_assets_result.message)

    if not messages:
        messages.append("No supported dependency files found to fix yet.")

    return CombinedFixResult(
        messages=messages,
        changed_files=changed_files,
    )
