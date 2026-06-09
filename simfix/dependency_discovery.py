"""Generic dependency-file discovery for simulator repositories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "build",
    "dist",
    "install",
    "log",
    "node_modules",
}


DEPENDENCY_FILE_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
    "Dockerfile",
    "package.xml",
    "CMakeLists.txt",
    "setup.py",
}


@dataclass(frozen=True)
class DiscoveredDependencyFiles:
    """Dependency files discovered in a repository."""

    requirements_txt: tuple[Path, ...]
    pyproject_toml: tuple[Path, ...]
    environment_files: tuple[Path, ...]
    dockerfiles: tuple[Path, ...]
    package_xml_files: tuple[Path, ...]
    cmake_lists_files: tuple[Path, ...]
    setup_py_files: tuple[Path, ...]

    @property
    def has_requirements_txt(self) -> bool:
        return bool(self.requirements_txt)

    @property
    def has_pyproject_toml(self) -> bool:
        return bool(self.pyproject_toml)

    @property
    def has_environment_file(self) -> bool:
        return bool(self.environment_files)

    @property
    def has_dockerfile(self) -> bool:
        return bool(self.dockerfiles)

    @property
    def has_ros_package(self) -> bool:
        return bool(self.package_xml_files)

    @property
    def has_cmake_lists(self) -> bool:
        return bool(self.cmake_lists_files)

    @property
    def has_setup_py(self) -> bool:
        return bool(self.setup_py_files)


def discover_dependency_files(
    repo_path: Path,
    *,
    max_depth: int = 4,
) -> DiscoveredDependencyFiles:
    """Discover dependency files in a repository up to a safe depth.

    This is generic and does not assume a specific simulator layout.
    It intentionally skips common build, cache, virtualenv, and VCS folders.
    """
    discovered_files = _walk_dependency_files(repo_path, max_depth=max_depth)

    return DiscoveredDependencyFiles(
        requirements_txt=_filter_by_name(discovered_files, "requirements.txt"),
        pyproject_toml=_filter_by_name(discovered_files, "pyproject.toml"),
        environment_files=tuple(
            path
            for path in discovered_files
            if path.name in {"environment.yml", "environment.yaml"}
        ),
        dockerfiles=_filter_by_name(discovered_files, "Dockerfile"),
        package_xml_files=_filter_by_name(discovered_files, "package.xml"),
        cmake_lists_files=_filter_by_name(discovered_files, "CMakeLists.txt"),
        setup_py_files=_filter_by_name(discovered_files, "setup.py"),
    )


def _walk_dependency_files(repo_path: Path, *, max_depth: int) -> tuple[Path, ...]:
    repo_path = repo_path.resolve()
    found: list[Path] = []

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(repo_path)

        if _should_skip_path(relative_path):
            continue

        if _depth(relative_path) > max_depth:
            continue

        if path.name in DEPENDENCY_FILE_NAMES:
            found.append(path)

    return tuple(sorted(found))


def _filter_by_name(paths: tuple[Path, ...], name: str) -> tuple[Path, ...]:
    return tuple(path for path in paths if path.name == name)


def _should_skip_path(relative_path: Path) -> bool:
    return any(part in IGNORED_DIRECTORY_NAMES for part in relative_path.parts)


def _depth(relative_path: Path) -> int:
    return len(relative_path.parts) - 1
