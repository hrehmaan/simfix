"""ROS environment detection helpers for SimFix recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RosEnvironmentInfo:
    """Detected ROS environment information."""

    project_type: str | None
    recommended_distribution: str | None
    recommended_ubuntu: str | None
    recommended_docker_image: str | None
    source: str | None


def detect_ros_environment_info(repo_path: Path) -> RosEnvironmentInfo | None:
    """Detect ROS project style and recommend a common compatible environment.

    This detection is generic and based on build-system signals, not repository
    names. It does not install ROS or modify files.
    """
    package_xml = repo_path / "package.xml"
    cmake_lists = repo_path / "CMakeLists.txt"

    package_text = _read_file(package_xml)
    cmake_text = _read_file(cmake_lists)
    combined_text = f"{package_text}\n{cmake_text}".lower()

    if not combined_text.strip():
        return None

    if _looks_like_ros2(combined_text):
        return RosEnvironmentInfo(
            project_type="ROS 2 / ament",
            recommended_distribution="Humble",
            recommended_ubuntu="Ubuntu 22.04",
            recommended_docker_image="osrf/ros:humble-desktop",
            source=_source_label(package_xml, cmake_lists),
        )

    if _looks_like_ros1(combined_text):
        return RosEnvironmentInfo(
            project_type="ROS 1 / catkin",
            recommended_distribution="Noetic",
            recommended_ubuntu="Ubuntu 20.04",
            recommended_docker_image="osrf/ros:noetic-desktop-full",
            source=_source_label(package_xml, cmake_lists),
        )

    if package_xml.exists():
        return RosEnvironmentInfo(
            project_type="ROS project",
            recommended_distribution=None,
            recommended_ubuntu=None,
            recommended_docker_image=None,
            source="package.xml",
        )

    return None


def _looks_like_ros2(text: str) -> bool:
    ros2_markers = [
        "ament_cmake",
        "ament_python",
        "ament_package",
        "find_package(ament_cmake",
        "<build_type>ament_cmake</build_type>",
        "<build_type>ament_python</build_type>",
        "rclpy",
        "rclcpp",
    ]
    return any(marker in text for marker in ros2_markers)


def _looks_like_ros1(text: str) -> bool:
    ros1_markers = [
        "catkin_package",
        "find_package(catkin",
        "<buildtool_depend>catkin</buildtool_depend>",
        "<build_depend>catkin</build_depend>",
        "<depend>roscpp</depend>",
        "<depend>rospy</depend>",
        "roslaunch",
    ]
    return any(marker in text for marker in ros1_markers)


def _read_file(path: Path) -> str:
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def _source_label(*paths: Path) -> str:
    existing_paths = [path.name for path in paths if path.exists()]

    if not existing_paths:
        return "ROS project files"

    return ", ".join(existing_paths)
