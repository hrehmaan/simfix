from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


def get_linux_os_release() -> tuple[str | None, str | None]:
    """Return Linux distribution name and version from /etc/os-release."""
    os_release_path = Path("/etc/os-release")

    if not os_release_path.exists():
        return None, None

    values: dict[str, str] = {}

    for line in os_release_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        values[key] = value.strip().strip('"')

    distro = values.get("NAME")
    version = values.get("VERSION_ID")

    return distro, version


def is_windows_subsystem_for_linux() -> bool:
    """Return True if running inside Windows Subsystem for Linux."""
    version_path = Path("/proc/version")

    if not version_path.exists():
        return False

    text = version_path.read_text(encoding="utf-8").lower()

    return "microsoft" in text or "wsl" in text


def get_nvidia_smi_field(field: str) -> str | None:
    """Return a single field from nvidia-smi query output."""
    if not command_exists("nvidia-smi"):
        return None

    result = subprocess.run(
        [
            "nvidia-smi",
            f"--query-gpu={field}",
            "--format=csv,noheader",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""

    return first_line.strip() or None


def get_cuda_toolkit_version() -> str | None:
    """Return CUDA toolkit version from nvcc if available."""
    if not command_exists("nvcc"):
        return None

    result = subprocess.run(
        ["nvcc", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        if "release" in line:
            return line.strip()

    return result.stdout.strip() or None


@dataclass(frozen=True)
class SystemInfo:
    """Basic system information relevant for simulator installation."""

    os_name: str
    os_version: str
    architecture: str
    python_version: str
    linux_distro: str | None
    linux_version: str | None
    is_wsl: bool
    git_available: bool
    docker_available: bool
    nvidia_gpu_available: bool
    nvidia_driver_version: str | None
    nvidia_cuda_version: str | None
    cuda_toolkit_version: str | None
    pip_available: bool
    uv_available: bool
    conda_available: bool
    mamba_available: bool


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
    linux_distro, linux_version = get_linux_os_release()
    return SystemInfo(
        os_name=platform.system(),
        os_version=platform.release(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        linux_distro=linux_distro,
        linux_version=linux_version,
        is_wsl=is_windows_subsystem_for_linux(),
        git_available=command_exists("git"),
        docker_available=command_exists("docker"),
        nvidia_gpu_available=has_nvidia_gpu(),
        nvidia_driver_version=get_nvidia_smi_field("driver_version"),
        nvidia_cuda_version=get_nvidia_smi_field("cuda_version"),
        cuda_toolkit_version=get_cuda_toolkit_version(),
        pip_available=command_exists("pip") or command_exists("pip3"),
        uv_available=command_exists("uv"),
        conda_available=command_exists("conda"),
        mamba_available=command_exists("mamba"),
    )
