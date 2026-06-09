from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class SystemInfo:
    """Basic system information relevant for simulator installation."""

    os_name: str
    os_version: str
    architecture: str
    python_version: str
    git_available: bool
    docker_available: bool
    nvidia_gpu_available: bool


def command_exists(command: str) -> bool:
    """Return True if a command exists on PATH."""
    return shutil.which(command) is not None


def has_nvidia_gpu() -> bool:
    """Return True if nvidia-smi is available and runs successfully."""
    if not command_exists("nvidia-smi"):
        return False

    result = subprocess.run(
        ["nvidia-smi"],
        check=False,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def get_system_info() -> SystemInfo:
    """Collect basic system information."""
    return SystemInfo(
        os_name=platform.system(),
        os_version=platform.release(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        git_available=command_exists("git"),
        docker_available=command_exists("docker"),
        nvidia_gpu_available=has_nvidia_gpu(),
    )
