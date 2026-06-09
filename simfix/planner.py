from __future__ import annotations

from dataclasses import dataclass

from simfix.analyzer import RepoAnalysis


@dataclass(frozen=True)
class InstallPlan:
    """Recommended installation plan for a repository."""

    recommended_mode: str
    reason: str
    steps: list[str]


def create_install_plan(analysis: RepoAnalysis) -> InstallPlan:
    """Create a basic installation plan from repository analysis."""
    ecosystems = analysis.detected_ecosystems

    if "docker" in ecosystems:
        return InstallPlan(
            recommended_mode="docker",
            reason=(
                "A Dockerfile was found, so container installation " "may be available."
            ),
            steps=[
                "Build the Docker image.",
                "Run the container.",
                "Test the simulator inside the container.",
            ],
        )

    if "ros" in ecosystems:
        return InstallPlan(
            recommended_mode="ros",
            reason="A package.xml file was found, so this looks like a ROS project.",
            steps=[
                "Create or use a ROS workspace.",
                "Install ROS dependencies using rosdep.",
                "Build the workspace with catkin or colcon.",
                "Source the workspace setup file.",
                "Run a launch file or example node.",
            ],
        )

    if "conda" in ecosystems:
        return InstallPlan(
            recommended_mode="conda",
            reason="An environment.yml file was found.",
            steps=[
                "Create the conda environment from environment.yml.",
                "Activate the environment.",
                "Install the project in editable mode if needed.",
                "Run tests or examples.",
            ],
        )

    if "python" in ecosystems:
        return InstallPlan(
            recommended_mode="python",
            reason="Python dependency files were found.",
            steps=[
                "Create a Python virtual environment.",
                "Install dependencies from requirements.txt or pyproject.toml.",
                "Install the project in editable mode if needed.",
                "Run tests or examples.",
            ],
        )

    if "cmake/c++" in ecosystems:
        return InstallPlan(
            recommended_mode="cmake",
            reason="A CMakeLists.txt file was found.",
            steps=[
                "Install system build tools and CMake.",
                "Create a build directory.",
                "Configure the project with cmake.",
                "Build the project.",
                "Run available examples or tests.",
            ],
        )

    return InstallPlan(
        recommended_mode="manual",
        reason="No known dependency file was found.",
        steps=[
            "Read the project README installation section.",
            "Check for custom install scripts.",
            "Install dependencies manually.",
            "Run available examples or tests.",
        ],
    )
