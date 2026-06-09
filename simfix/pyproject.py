from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class PyProjectInfo:
    """Basic information extracted from pyproject.toml."""

    project_name: str | None
    dependencies: list[str]
    optional_dependencies: dict[str, list[str]]
    build_system_requires: list[str]


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [item for item in value if isinstance(item, str)]


def parse_pyproject(path: str | Path) -> PyProjectInfo | None:
    """Parse pyproject.toml and extract common dependency fields."""
    pyproject_path = Path(path).expanduser().resolve()

    if not pyproject_path.exists():
        return None

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    project = data.get("project", {})
    build_system = data.get("build-system", {})
    tool = data.get("tool", {})
    poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}

    project_name = None
    dependencies: list[str] = []
    optional_dependencies: dict[str, list[str]] = {}
    build_system_requires: list[str] = []

    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str):
            project_name = name

        dependencies.extend(_as_string_list(project.get("dependencies")))

        raw_optional = project.get("optional-dependencies", {})
        if isinstance(raw_optional, dict):
            for group_name, group_deps in raw_optional.items():
                if isinstance(group_name, str):
                    optional_dependencies[group_name] = _as_string_list(group_deps)

    if isinstance(build_system, dict):
        build_system_requires = _as_string_list(build_system.get("requires"))

    if isinstance(poetry, dict):
        poetry_name = poetry.get("name")
        if project_name is None and isinstance(poetry_name, str):
            project_name = poetry_name

        poetry_dependencies = poetry.get("dependencies", {})
        if isinstance(poetry_dependencies, dict):
            for name, requirement in poetry_dependencies.items():
                if name == "python":
                    continue

                if isinstance(requirement, str):
                    dependencies.append(f"{name}{requirement}")
                else:
                    dependencies.append(str(name))

        poetry_groups = poetry.get("group", {})
        if isinstance(poetry_groups, dict):
            for group_name, group_data in poetry_groups.items():
                if not isinstance(group_name, str) or not isinstance(group_data, dict):
                    continue

                group_dependencies = group_data.get("dependencies", {})
                if not isinstance(group_dependencies, dict):
                    continue

                optional_dependencies[group_name] = [
                    f"{name}{requirement}"
                    if isinstance(requirement, str)
                    else str(name)
                    for name, requirement in group_dependencies.items()
                ]

    return PyProjectInfo(
        project_name=project_name,
        dependencies=list(dict.fromkeys(dependencies)),
        optional_dependencies=optional_dependencies,
        build_system_requires=build_system_requires,
    )
