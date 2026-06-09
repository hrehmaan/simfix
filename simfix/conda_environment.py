from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CondaEnvironment:
    """Parsed conda environment information."""

    name: str | None
    conda_dependencies: list[str]
    pip_dependencies: list[str]


def parse_conda_environment(path: str | Path) -> CondaEnvironment | None:
    """Parse a conda environment.yml/environment.yaml file."""
    environment_path = Path(path).expanduser().resolve()

    if not environment_path.exists():
        return None

    data = yaml.safe_load(environment_path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        return None

    name = data.get("name")
    raw_dependencies = data.get("dependencies", [])

    conda_dependencies: list[str] = []
    pip_dependencies: list[str] = []

    if not isinstance(raw_dependencies, list):
        return CondaEnvironment(
            name=name if isinstance(name, str) else None,
            conda_dependencies=[],
            pip_dependencies=[],
        )

    for dependency in raw_dependencies:
        if isinstance(dependency, str):
            conda_dependencies.append(dependency)
        elif isinstance(dependency, dict):
            pip_entries: Any = dependency.get("pip")
            if isinstance(pip_entries, list):
                pip_dependencies.extend(
                    item for item in pip_entries if isinstance(item, str)
                )

    return CondaEnvironment(
        name=name if isinstance(name, str) else None,
        conda_dependencies=conda_dependencies,
        pip_dependencies=pip_dependencies,
    )
