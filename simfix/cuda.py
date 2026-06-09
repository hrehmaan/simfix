"""CUDA version detection helpers for SimFix recommendations."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CudaVersionInfo:
    """Detected CUDA version information."""

    repo_cuda_version: tuple[int, int] | None
    system_cuda_version: tuple[int, int] | None
    repo_cuda_source: str | None


def detect_cuda_version_info(repo_path: Path) -> CudaVersionInfo:
    """Detect repository CUDA requirement and system CUDA capability."""
    repo_cuda_version, repo_cuda_source = detect_repo_cuda_version(repo_path)
    system_cuda_version = detect_system_cuda_version()

    return CudaVersionInfo(
        repo_cuda_version=repo_cuda_version,
        system_cuda_version=system_cuda_version,
        repo_cuda_source=repo_cuda_source,
    )


def detect_repo_cuda_version(
    repo_path: Path,
) -> tuple[tuple[int, int] | None, str | None]:
    """Detect CUDA version requested by repository files.

    This is intentionally generic. It checks common simulator/deep-learning
    signals such as Docker base images and CUDA-specific dependency names.
    """
    dockerfile = repo_path / "Dockerfile"
    if dockerfile.exists():
        version = _detect_cuda_version_from_text(dockerfile.read_text(encoding="utf-8"))
        if version is not None:
            return version, "Dockerfile"

    dependency_files = [
        repo_path / "requirements.txt",
        repo_path / "pyproject.toml",
        repo_path / "setup.py",
        repo_path / "environment.yml",
        repo_path / "environment.yaml",
    ]

    for dependency_file in dependency_files:
        if dependency_file.exists():
            version = _detect_cuda_version_from_text(
                dependency_file.read_text(encoding="utf-8")
            )
            if version is not None:
                return version, dependency_file.name

    return None, None


def detect_system_cuda_version() -> tuple[int, int] | None:
    """Detect CUDA version supported by the NVIDIA driver using nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return _parse_nvidia_smi_cuda_version(result.stdout + result.stderr)


def is_cuda_version_mismatch(
    repo_cuda_version: tuple[int, int] | None,
    system_cuda_version: tuple[int, int] | None,
) -> bool:
    """Return True if the repo appears to require newer CUDA than the system."""
    if repo_cuda_version is None or system_cuda_version is None:
        return False

    return repo_cuda_version > system_cuda_version


def _detect_cuda_version_from_text(text: str) -> tuple[int, int] | None:
    """Detect CUDA version from generic text."""
    normalized = text.lower()

    detected_versions: list[tuple[int, int]] = []

    explicit_patterns = [
        r"nvidia/cuda:(\d+)\.(\d+)",
        r"cuda[-_]?(\d+)[\._-](\d+)",
    ]

    for pattern in explicit_patterns:
        for match in re.finditer(pattern, normalized):
            detected_versions.append((int(match.group(1)), int(match.group(2))))

    for match in re.finditer(r"cuda[-_]?(\d+)x", normalized):
        detected_versions.append((int(match.group(1)), 0))

    for match in re.finditer(r"cu(\d{2,3})", normalized):
        detected_versions.append(_parse_compact_cuda_version(match.group(1)))

    if not detected_versions:
        return None

    return max(detected_versions)


def _parse_nvidia_smi_cuda_version(text: str) -> tuple[int, int] | None:
    """Parse CUDA version from nvidia-smi output."""
    match = re.search(r"cuda version:\s*(\d+)\.(\d+)", text.lower())
    if match is None:
        return None

    return int(match.group(1)), int(match.group(2))


def _parse_compact_cuda_version(version: str) -> tuple[int, int]:
    """Parse compact CUDA version strings such as cu118 or cu121."""
    if len(version) == 2:
        return int(version[0]), int(version[1])

    return int(version[:-1]), int(version[-1])
