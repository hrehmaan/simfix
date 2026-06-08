from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoAnalysis:
    """Basic analysis result for a simulator repository."""

    repo_path: Path
    has_requirements_txt: bool
    has_pyproject_toml: bool
    has_environment_yml: bool
    has_dockerfile: bool
    has_package_xml: bool
    has_cmake: bool

    @property
    def detected_ecosystems(self) -> list[str]:
        """Return detected project ecosystems."""
        ecosystems: list[str] = []

        if self.has_requirements_txt or self.has_pyproject_toml:
            ecosystems.append("python")

        if self.has_environment_yml:
            ecosystems.append("conda")

        if self.has_dockerfile:
            ecosystems.append("docker")

        if self.has_package_xml:
            ecosystems.append("ros")

        if self.has_cmake:
            ecosystems.append("cmake/c++")

        if not ecosystems:
            ecosystems.append("unknown")

        return ecosystems


def analyze_repo(repo_path: str | Path) -> RepoAnalysis:
    """Analyze a local repository path and detect common dependency files."""
    path = Path(repo_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path}")

    return RepoAnalysis(
        repo_path=path,
        has_requirements_txt=(path / "requirements.txt").exists(),
        has_pyproject_toml=(path / "pyproject.toml").exists(),
        has_environment_yml=(path / "environment.yml").exists()
        or (path / "environment.yaml").exists(),
        has_dockerfile=(path / "Dockerfile").exists(),
        has_package_xml=(path / "package.xml").exists(),
        has_cmake=(path / "CMakeLists.txt").exists(),
    )
