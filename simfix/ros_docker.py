from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simfix.analyzer import analyze_repo


@dataclass(frozen=True)
class RosDockerFixResult:
    """Result of creating a ROS Dockerfile."""

    file_path: Path
    changed: bool
    message: str


def _ros1_dockerfile() -> str:
    """Return a Dockerfile for ROS 1 catkin projects."""
    return """FROM osrf/ros:noetic-desktop-full

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y \\
    python3-pip \\
    python3-rosdep \\
    python3-catkin-tools \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . /workspace/src/simfix_project

RUN rosdep update || true
RUN rosdep install --from-paths /workspace/src --ignore-src -r -y || true

WORKDIR /workspace

RUN source /opt/ros/noetic/setup.bash && \\
    catkin build
"""


def _ros2_dockerfile() -> str:
    """Return a Dockerfile for ROS 2 ament projects."""
    return """FROM osrf/ros:humble-desktop

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y \\
    python3-pip \\
    python3-rosdep \\
    python3-colcon-common-extensions \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . /workspace/src/simfix_project

RUN rosdep update || true
RUN rosdep install --from-paths /workspace/src --ignore-src -r -y || true

WORKDIR /workspace

RUN source /opt/ros/humble/setup.bash && \\
    colcon build
"""


def create_ros_dockerfile(repo_path: str | Path) -> RosDockerFixResult | None:
    """Create a Dockerfile for ROS projects.

    This creates Dockerfile only when package.xml exists and Dockerfile does not.
    """
    path = Path(repo_path).expanduser().resolve()
    analysis = analyze_repo(path)

    if not analysis.has_package_xml:
        return None

    dockerfile_path = path / "Dockerfile"

    if dockerfile_path.exists():
        return RosDockerFixResult(
            file_path=dockerfile_path,
            changed=False,
            message="Dockerfile already exists. SimFix did not overwrite it.",
        )

    build_system = None

    if analysis.ros_package_info is not None:
        build_system = analysis.ros_package_info.build_system

    if build_system == "ament":
        dockerfile_text = _ros2_dockerfile()
        message = "Created ROS 2 Humble Dockerfile."
    else:
        dockerfile_text = _ros1_dockerfile()
        message = "Created ROS 1 Noetic Dockerfile."

    dockerfile_path.write_text(dockerfile_text, encoding="utf-8")

    return RosDockerFixResult(
        file_path=dockerfile_path,
        changed=True,
        message=message,
    )
