from __future__ import annotations

from simfix.analyzer import RepoAnalysis
from simfix.system import SystemInfo

ROS_UBUNTU_HINTS = {
    "melodic": "18.04",
    "noetic": "20.04",
    "humble": "22.04",
    "jazzy": "24.04",
}


def _detect_ros_distro_hint(analysis: RepoAnalysis) -> str | None:
    """Detect possible ROS distro hints from parsed dependency names."""
    if analysis.ros_package_info is None:
        return None

    dependencies = [
        dependency.lower() for dependency in analysis.ros_package_info.all_dependencies
    ]

    joined_dependencies = " ".join(dependencies)

    for distro in ROS_UBUNTU_HINTS:
        if distro in joined_dependencies:
            return distro

    ros_info = analysis.ros_package_info

    if ros_info.build_system == "catkin":
        return "noetic"

    if ros_info.build_system == "ament":
        return "humble"

    return None


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

    ros_distro_hint = _detect_ros_distro_hint(analysis)

    if (
        ros_distro_hint is not None
        and system_info.linux_version is not None
        and ROS_UBUNTU_HINTS[ros_distro_hint] != system_info.linux_version
    ):
        warnings.append(
            f"ROS {ros_distro_hint} project detected, which is commonly used with "
            f"Ubuntu {ROS_UBUNTU_HINTS[ros_distro_hint]}, but this system appears "
            f"to be Ubuntu {system_info.linux_version}."
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
