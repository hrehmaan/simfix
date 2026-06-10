"""ROS environment detection helpers for SimFix recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from simfix.dependency_discovery import discover_dependency_files


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
    names. It supports both root-level ROS packages and nested ROS workspaces.
    It does not install ROS or modify files.
    """
    discovered_files = discover_dependency_files(repo_path)

    package_xml_files = discovered_files.package_xml_files
    cmake_lists_files = discovered_files.cmake_lists_files

    if not package_xml_files and not cmake_lists_files:
        return None

    package_text = "\n".join(_read_file(path) for path in package_xml_files)
    cmake_text = "\n".join(_read_file(path) for path in cmake_lists_files)
    combined_text = f"{package_text}\n{cmake_text}".lower()

    source = _source_label(*package_xml_files, *cmake_lists_files)

    if _looks_like_ros2(combined_text):
        return RosEnvironmentInfo(
            project_type="ROS 2 / ament",
            recommended_distribution="Humble",
            recommended_ubuntu="Ubuntu 22.04",
            recommended_docker_image="osrf/ros:humble-desktop",
            source=source,
        )

    if _looks_like_ros1(combined_text):
        return RosEnvironmentInfo(
            project_type="ROS 1 / catkin",
            recommended_distribution="Noetic",
            recommended_ubuntu="Ubuntu 20.04",
            recommended_docker_image="osrf/ros:noetic-desktop-full",
            source=source,
        )

    return RosEnvironmentInfo(
        project_type="ROS project",
        recommended_distribution=None,
        recommended_ubuntu=None,
        recommended_docker_image=None,
        source=source,
    )


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


def _pluralize(count: int, singular: str, plural: str) -> str:
    if count == 1:
        return f"1 {singular}"

    return f"{count} {plural}"


def _source_label(*paths: Path) -> str:
    existing_paths = [path for path in paths if path.exists()]

    if not existing_paths:
        return "ROS project files"

    package_xml_count = sum(path.name == "package.xml" for path in existing_paths)
    cmake_count = sum(path.name == "CMakeLists.txt" for path in existing_paths)

    labels: list[str] = []

    if package_xml_count:
        labels.append(
            _pluralize(package_xml_count, "package.xml file", "package.xml files")
        )

    if cmake_count:
        labels.append(
            _pluralize(cmake_count, "CMakeLists.txt file", "CMakeLists.txt files")
        )

    if labels:
        return " and ".join(labels)

    unique_names = sorted({path.name for path in existing_paths})
    return ", ".join(unique_names)
