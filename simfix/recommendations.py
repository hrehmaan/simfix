from __future__ import annotations

from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class Recommendation:
    """A safe recommendation for a system or vendor dependency."""

    category: str
    title: str
    status: str
    reason: str
    suggestion: str


def generate_recommendations(
    dependencies: list[str],
    detected_ecosystems: list[str],
    python_version: tuple[int, int] | None = None,
) -> list[Recommendation]:
    """Generate safe system and vendor dependency recommendations.

    This function does not install drivers, ROS, CUDA, or vendor tools.
    It only detects likely requirements and returns guidance.
    """
    recommendations: list[Recommendation] = []

    normalized_dependencies = [dependency.lower() for dependency in dependencies]
    normalized_ecosystems = [ecosystem.lower() for ecosystem in detected_ecosystems]

    if python_version is None:
        python_version = sys.version_info[:2]

    has_isaacgym = any(
        "isaacgym" in dependency for dependency in normalized_dependencies
    )
    has_isaacsim = any(
        "isaacsim" in dependency or "omni.isaac" in dependency
        for dependency in normalized_dependencies
    )
    has_cuda_dependency = any(
        _has_cuda_keyword(dependency) for dependency in normalized_dependencies
    )
    has_ros = "ros" in normalized_ecosystems

    has_old_pinned_dependency = any(
        _has_old_pinned_dependency(dependency) for dependency in normalized_dependencies
    )

    if has_isaacgym:
        recommendations.append(
            Recommendation(
                category="Vendor-managed dependency",
                title="NVIDIA Isaac Gym required",
                status="Manual installation required",
                reason=(
                    "The dependency 'isaacgym' was detected, but it is not "
                    "available as a normal PyPI package."
                ),
                suggestion=(
                    "Install NVIDIA Isaac Gym manually in a compatible Linux "
                    "environment with NVIDIA GPU support. If the local machine "
                    "is not suitable, use an HPC GPU node or cloud GPU instance."
                ),
            )
        )

    if has_isaacsim:
        recommendations.append(
            Recommendation(
                category="Vendor-managed dependency",
                title="NVIDIA Isaac Sim required",
                status="Manual installation required",
                reason=(
                    "Isaac Sim or omni.isaac dependencies were detected. "
                    "These are NVIDIA-managed dependencies."
                ),
                suggestion=(
                    "Install Isaac Sim using NVIDIA's official installation "
                    "method. Use a supported system with compatible NVIDIA GPU "
                    "drivers."
                ),
            )
        )

    if has_isaacgym or has_isaacsim or has_cuda_dependency:
        recommendations.append(
            Recommendation(
                category="GPU/CUDA",
                title="CUDA-compatible environment recommended",
                status="Check required",
                reason=(
                    "GPU/CUDA-related dependencies were detected in the " "repository."
                ),
                suggestion=(
                    "Use a compatible Linux/NVIDIA GPU environment. If the "
                    "local GPU is not CUDA-compatible, consider a Docker setup "
                    "on a compatible machine, an HPC GPU node, a cloud GPU "
                    "instance, or CPU-only mode if the simulator supports it."
                ),
            )
        )

    if has_ros:
        recommendations.append(
            Recommendation(
                category="ROS",
                title="ROS environment required",
                status="Manual installation required",
                reason="ROS package files were detected in the repository.",
                suggestion=(
                    "Use a matching ROS Docker image or install the correct "
                    "ROS distribution manually. For ROS 1/catkin projects, "
                    "ROS Noetic on Ubuntu 20.04 is commonly used. For ROS "
                    "2/ament projects, ROS Humble on Ubuntu 22.04 is commonly "
                    "used."
                ),
            )
        )

    if has_old_pinned_dependency and python_version >= (3, 13):
        recommendations.append(
            Recommendation(
                category="Python environment",
                title="Older pinned dependencies detected",
                status="Python version compatibility check recommended",
                reason=(
                    "This repository contains older pinned dependencies that may "
                    f"not install cleanly on Python {python_version[0]}.{python_version[1]}."
                ),
                suggestion=(
                    "Use Python 3.10 or 3.11 in a virtual environment for better "
                    "compatibility before installing the project dependencies."
                ),
            )
        )

    return recommendations


def _has_cuda_keyword(dependency: str) -> bool:
    """Return True if a dependency suggests GPU/CUDA requirements."""
    cuda_keywords = [
        "cuda",
        "cudnn",
        "cupy",
        "pytorch3d",
        "onnxruntime-gpu",
        "tensorflow-gpu",
        "jax[cuda",
        "numba.cuda",
    ]

    return any(keyword in dependency for keyword in cuda_keywords)


def _has_old_pinned_dependency(dependency: str) -> bool:
    """Return True when a dependency is pinned to an old version.

    This is a conservative heuristic used for Python-version compatibility
    recommendations. It does not modify dependencies.
    """
    normalized = dependency.lower().strip()

    if "==" not in normalized:
        return False

    package_name, version = normalized.split("==", maxsplit=1)
    package_name = package_name.strip()
    version = version.strip()

    old_version_thresholds = {
        "numpy": (1, 24),
        "scipy": (1, 10),
        "networkx": (3, 0),
        "pandas": (2, 0),
        "matplotlib": (3, 7),
        "gym": (1, 0),
        "urdfpy": (0, 1),
    }

    if package_name not in old_version_thresholds:
        return False

    parsed_version = _parse_version_prefix(version)
    if parsed_version is None:
        return False

    return parsed_version < old_version_thresholds[package_name]


def _parse_version_prefix(version: str) -> tuple[int, ...] | None:
    """Parse the numeric prefix of a dependency version.

    Examples:
        1.23.0 -> (1, 23, 0)
        2.2 -> (2, 2)
        0.0.22 -> (0, 0, 22)
    """
    parts: list[int] = []

    for part in version.split("."):
        number = ""
        for character in part:
            if character.isdigit():
                number += character
            else:
                break

        if not number:
            break

        parts.append(int(number))

    if not parts:
        return None

    return tuple(parts)
