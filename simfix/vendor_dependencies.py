"""Vendor and system dependency recommendations for SimFix."""

from __future__ import annotations

from dataclasses import dataclass

from simfix.recommendation_types import Recommendation


@dataclass(frozen=True)
class VendorDependencyRule:
    """Rule describing a dependency that needs manual/system guidance."""

    patterns: tuple[str, ...]
    category: str
    title: str
    status: str
    reason: str
    suggestion: str


VENDOR_DEPENDENCY_RULES: tuple[VendorDependencyRule, ...] = (
    VendorDependencyRule(
        patterns=("isaacgym",),
        category="Vendor-managed dependency",
        title="NVIDIA Isaac Gym required",
        status="Manual installation required",
        reason=(
            "NVIDIA Isaac Gym was detected. It is distributed separately from "
            "normal PyPI packages and usually requires a compatible Linux/NVIDIA "
            "GPU environment."
        ),
        suggestion=(
            "Install NVIDIA Isaac Gym manually using the vendor installation "
            "instructions, or use an HPC/cloud GPU environment prepared for "
            "Isaac Gym workloads."
        ),
    ),
    VendorDependencyRule(
        patterns=("isaacsim", "omni.isaac"),
        category="Vendor-managed dependency",
        title="NVIDIA Isaac Sim required",
        status="Manual installation required",
        reason=(
            "NVIDIA Isaac Sim or Omniverse Isaac dependencies were detected. "
            "These dependencies are managed through NVIDIA tooling rather than "
            "normal Python package installation."
        ),
        suggestion=(
            "Install Isaac Sim using NVIDIA's supported installation method on "
            "a compatible system, or use a prepared workstation/HPC/cloud image."
        ),
    ),
    VendorDependencyRule(
        patterns=("mujoco-py",),
        category="System dependency",
        title="MuJoCo system dependencies may be required",
        status="System dependency check recommended",
        reason=(
            "mujoco-py was detected. It often requires MuJoCo binaries and "
            "OpenGL/system libraries in addition to Python packages."
        ),
        suggestion=(
            "Check MuJoCo, OpenGL, and compiler dependencies before installing. "
            "A Docker environment is often safer for reproducible simulator setup."
        ),
    ),
    VendorDependencyRule(
        patterns=("pytorch3d",),
        category="GPU/ML dependency",
        title="PyTorch3D compatibility check recommended",
        status="Version compatibility check recommended",
        reason=(
            "pytorch3d was detected. PyTorch3D compatibility depends on Python, "
            "PyTorch, CUDA, and platform versions."
        ),
        suggestion=(
            "Use a compatible PyTorch/PyTorch3D/CUDA combination. Prefer a known "
            "working Docker or conda environment when available."
        ),
    ),
    VendorDependencyRule(
        patterns=("cupy-cuda", "onnxruntime-gpu", "tensorflow-gpu"),
        category="GPU runtime dependency",
        title="CUDA runtime compatibility check recommended",
        status="Version compatibility check recommended",
        reason=(
            "CUDA-based Python dependencies were detected. These often require "
            "matching CUDA/cuDNN/NVIDIA driver support."
        ),
        suggestion=(
            "Check that the CUDA runtime, cuDNN, NVIDIA driver, and package "
            "versions are compatible. Use a CUDA-compatible Docker image or "
            "prepared GPU environment when possible."
        ),
    ),
)


def detect_vendor_dependency_recommendations(
    dependencies: list[str],
) -> list[Recommendation]:
    """Return recommendations for vendor/system dependencies.

    This is data-driven and generic. It checks dependency patterns, not
    repository names.
    """
    normalized_dependencies = [dependency.lower() for dependency in dependencies]
    recommendations: list[Recommendation] = []

    for rule in VENDOR_DEPENDENCY_RULES:
        if _rule_matches(rule, normalized_dependencies):
            recommendations.append(
                Recommendation(
                    category=rule.category,
                    title=rule.title,
                    status=rule.status,
                    reason=rule.reason,
                    suggestion=rule.suggestion,
                )
            )

    return recommendations


def _rule_matches(
    rule: VendorDependencyRule,
    normalized_dependencies: list[str],
) -> bool:
    return any(
        pattern in dependency
        for pattern in rule.patterns
        for dependency in normalized_dependencies
    )
