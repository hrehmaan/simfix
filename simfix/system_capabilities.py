"""System capability detection used by SimFix recommendations."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class SystemCapabilities:
    """Detected system capabilities relevant to simulator installation."""

    has_docker: bool
    has_nvidia_smi: bool
    has_nvidia_container_runtime: bool


def detect_system_capabilities() -> SystemCapabilities:
    """Detect system capabilities without modifying the system."""
    return SystemCapabilities(
        has_docker=shutil.which("docker") is not None,
        has_nvidia_smi=shutil.which("nvidia-smi") is not None,
        has_nvidia_container_runtime=_has_nvidia_container_runtime(),
    )


def _has_nvidia_container_runtime() -> bool:
    """Return True if Docker appears to support NVIDIA GPU containers."""
    if shutil.which("docker") is None:
        return False

    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{json .Runtimes}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    output = result.stdout.lower() + result.stderr.lower()

    return "nvidia" in output
