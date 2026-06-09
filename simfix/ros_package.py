from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


def _detect_build_system(build_tool_dependencies: list[str]) -> str | None:
    """Detect ROS build system from build tool dependencies."""
    dependency_set = set(build_tool_dependencies)

    if "catkin" in dependency_set:
        return "catkin"

    if "ament_cmake" in dependency_set or "ament_python" in dependency_set:
        return "ament"

    return None


@dataclass(frozen=True)
class ROSPackageInfo:
    """Basic information extracted from a ROS package.xml file."""

    name: str | None
    build_system: str | None
    build_tool_dependencies: list[str]
    build_dependencies: list[str]
    execution_dependencies: list[str]
    test_dependencies: list[str]

    @property
    def all_dependencies(self) -> list[str]:
        """Return all dependency names without duplicates."""
        dependencies = (
            self.build_tool_dependencies
            + self.build_dependencies
            + self.execution_dependencies
            + self.test_dependencies
        )

        return list(dict.fromkeys(dependencies))


def _find_text(root: ET.Element, tag: str) -> str | None:
    element = root.find(tag)

    if element is None or element.text is None:
        return None

    return element.text.strip()


def _find_all_text(root: ET.Element, tags: list[str]) -> list[str]:
    values: list[str] = []

    for tag in tags:
        for element in root.findall(tag):
            if element.text is not None:
                values.append(element.text.strip())

    return values


def parse_ros_package(path: str | Path) -> ROSPackageInfo | None:
    """Parse a ROS package.xml file."""
    package_path = Path(path).expanduser().resolve()

    if not package_path.exists():
        return None

    try:
        tree = ET.parse(package_path)
    except ET.ParseError:
        return None

    root = tree.getroot()

    build_tool_dependencies = _find_all_text(root, ["buildtool_depend"])

    return ROSPackageInfo(
        name=_find_text(root, "name"),
        build_system=_detect_build_system(build_tool_dependencies),
        build_tool_dependencies=build_tool_dependencies,
        build_dependencies=_find_all_text(
            root,
            ["build_depend", "depend"],
        ),
        execution_dependencies=_find_all_text(
            root,
            ["exec_depend", "run_depend", "depend"],
        ),
        test_dependencies=_find_all_text(root, ["test_depend"]),
    )
