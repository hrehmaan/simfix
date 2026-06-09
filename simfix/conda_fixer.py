from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from simfix.pypi import normalize_requirement_name


@dataclass(frozen=True)
class CondaFixResult:
    """Result of fixing a conda environment file."""

    file_path: Path
    changed: bool
    message: str


def _dependency_name(dependency: str) -> str:
    """Return normalized dependency name without version constraints."""
    separators = ["==", ">=", "<=", "!=", "~=", "=", ">", "<"]

    for separator in separators:
        if separator in dependency:
            return dependency.split(separator, maxsplit=1)[0].strip().lower()

    return dependency.strip().lower()


def _is_more_specific(new_dependency: str, old_dependency: str) -> bool:
    """Return True if new dependency has more version information."""
    version_symbols = ["==", ">=", "<=", "!=", "~=", "=", ">", "<"]

    new_score = sum(symbol in new_dependency for symbol in version_symbols)
    old_score = sum(symbol in old_dependency for symbol in version_symbols)

    return new_score >= old_score


def _deduplicate_dependencies(dependencies: list[str]) -> list[str]:
    """Remove duplicate dependencies while keeping the more specific entry."""
    normalized: dict[str, str] = {}

    for dependency in dependencies:
        name = _dependency_name(dependency)

        if name not in normalized:
            normalized[name] = dependency
            continue

        if _is_more_specific(dependency, normalized[name]):
            normalized[name] = dependency

    return list(normalized.values())


def _deduplicate_pip_dependencies(dependencies: list[str]) -> list[str]:
    """Remove duplicate pip dependencies while keeping the more specific entry."""
    normalized: dict[str, str] = {}

    for dependency in dependencies:
        name = normalize_requirement_name(dependency).lower()

        if name not in normalized:
            normalized[name] = dependency
            continue

        if _is_more_specific(dependency, normalized[name]):
            normalized[name] = dependency

    return list(normalized.values())


def fix_conda_environment_file(repo_path: str | Path) -> CondaFixResult | None:
    """Fix environment.yml or environment.yaml in place."""
    path = Path(repo_path).expanduser().resolve()

    environment_path = path / "environment.yml"

    if not environment_path.exists():
        environment_path = path / "environment.yaml"

    if not environment_path.exists():
        return None

    old_text = environment_path.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(old_text) or {}

    dependencies = data.get("dependencies")

    if not isinstance(dependencies, list):
        return CondaFixResult(
            file_path=environment_path,
            changed=False,
            message="environment.yml has no valid dependencies list.",
        )

    conda_dependencies: list[str] = []
    pip_dependency_block: dict[str, list[str]] | None = None
    other_entries: list[Any] = []

    for dependency in dependencies:
        if isinstance(dependency, str):
            conda_dependencies.append(dependency)
        elif isinstance(dependency, dict) and "pip" in dependency:
            pip_values = dependency.get("pip", [])

            if isinstance(pip_values, list):
                pip_dependency_block = {
                    "pip": _deduplicate_pip_dependencies(
                        [str(value) for value in pip_values]
                    )
                }
            else:
                other_entries.append(dependency)
        else:
            other_entries.append(dependency)

    fixed_dependencies: list[Any] = []
    fixed_dependencies.extend(_deduplicate_dependencies(conda_dependencies))
    fixed_dependencies.extend(other_entries)

    if pip_dependency_block is not None:
        fixed_dependencies.append(pip_dependency_block)

    data["dependencies"] = fixed_dependencies

    new_text = yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
    )

    changed = old_text != new_text

    if changed:
        environment_path.write_text(new_text, encoding="utf-8")

    return CondaFixResult(
        file_path=environment_path,
        changed=changed,
        message="environment.yml cleaned successfully.",
    )
