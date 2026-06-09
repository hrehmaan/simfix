from __future__ import annotations

from simfix.analyzer import RepoAnalysis
from simfix.system import SystemInfo


def generate_compatibility_warnings(
    analysis: RepoAnalysis,
    system_info: SystemInfo,
) -> list[str]:
    """Generate compatibility warnings from repo analysis and system information."""
    warnings: list[str] = []
    ecosystems = analysis.detected_ecosystems

    if "docker" in ecosystems and not system_info.docker_available:
        warnings.append("Dockerfile detected, but Docker was not found on this system.")

    if (
        "conda" in ecosystems
        and not system_info.conda_available
        and not system_info.mamba_available
    ):
        warnings.append(
            "Conda environment detected, but neither conda nor mamba was found."
        )

    if (
        "python" in ecosystems
        and not system_info.pip_available
        and not system_info.uv_available
    ):
        warnings.append("Python project detected, but neither pip nor uv was found.")

    if "ros" in ecosystems and system_info.os_name != "Linux":
        warnings.append(
            "ROS project detected, but the current system is not Linux. "
            "Docker or a Linux machine may be needed."
        )

    if "cmake/c++" in ecosystems and system_info.os_name == "Darwin":
        warnings.append(
            "CMake/C++ project detected on macOS. Some simulator dependencies "
            "may require Linux-specific packages."
        )

    if "unknown" in ecosystems:
        warnings.append(
            "No common dependency files were detected. Manual inspection is needed."
        )

    return warnings
