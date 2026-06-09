from __future__ import annotations

from dataclasses import dataclass


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
) -> list[Recommendation]:
    """Generate safe system and vendor dependency recommendations.

    This function does not install drivers, ROS, CUDA, or vendor tools.
    It only detects likely requirements and returns guidance.
    """
    recommendations: list[Recommendation] = []

    normalized_dependencies = [dependency.lower() for dependency in dependencies]

    normalized_ecosystems = [ecosystem.lower() for ecosystem in detected_ecosystems]

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
