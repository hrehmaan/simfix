"""Workspace summary helpers for SimFix."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from simfix.dependency_discovery import discover_dependency_files


@dataclass(frozen=True)
class RosPackageSummary:
    """Summary of a detected ROS package."""

    name: str
    path: Path


@dataclass(frozen=True)
class WorkspaceSummary:
    """Summary of detected workspace components."""

    ros_packages: tuple[RosPackageSummary, ...]


def summarize_workspace(repo_path: Path) -> WorkspaceSummary:
    """Summarize detected workspace components.

    This function is generic and based on discovered dependency files,
    not repository names.
    """
    discovered_files = discover_dependency_files(repo_path)

    ros_packages = tuple(
        package
        for package_xml in discovered_files.package_xml_files
        if (package := _parse_ros_package_summary(package_xml)) is not None
    )

    return WorkspaceSummary(ros_packages=ros_packages)


def _parse_ros_package_summary(package_xml: Path) -> RosPackageSummary | None:
    text = package_xml.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"<name>\s*([^<]+?)\s*</name>", text)

    if match is None:
        return None

    name = match.group(1).strip()
    if not name:
        return None

    return RosPackageSummary(
        name=name,
        path=package_xml.parent,
    )
