from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simfix.cmake import CMakeInfo, parse_cmake_file
from simfix.conda_environment import CondaEnvironment, parse_conda_environment
from simfix.dockerfile import DockerfileInfo, parse_dockerfile
from simfix.pyproject import PyProjectInfo, parse_pyproject
from simfix.python_requirements import parse_requirements_file
from simfix.ros_package import ROSPackageInfo, parse_ros_package


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
    python_requirements: list[str]
    conda_environment: CondaEnvironment | None
    dockerfile_info: DockerfileInfo | None
    ros_package_info: ROSPackageInfo | None
    cmake_info: CMakeInfo | None
    pyproject_info: PyProjectInfo | None

    @property
    def all_python_dependencies(self) -> list[str]:
        """Return Python dependencies from requirements.txt and pyproject.toml."""
        dependencies = list(self.python_requirements)

        if self.pyproject_info is not None:
            dependencies.extend(self.pyproject_info.dependencies)

        return list(dict.fromkeys(dependencies))

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

    requirements_path = path / "requirements.txt"
    environment_path = path / "environment.yml"
    if not environment_path.exists():
        environment_path = path / "environment.yaml"

    dockerfile_path = path / "Dockerfile"
    package_xml_path = path / "package.xml"
    cmake_path = path / "CMakeLists.txt"
    pyproject_path = path / "pyproject.toml"

    return RepoAnalysis(
        repo_path=path,
        has_requirements_txt=requirements_path.exists(),
        has_environment_yml=(path / "environment.yml").exists()
        or (path / "environment.yaml").exists(),
        python_requirements=parse_requirements_file(requirements_path),
        conda_environment=parse_conda_environment(environment_path),
        has_dockerfile=dockerfile_path.exists(),
        dockerfile_info=parse_dockerfile(dockerfile_path),
        has_package_xml=package_xml_path.exists(),
        ros_package_info=parse_ros_package(package_xml_path),
        has_cmake=cmake_path.exists(),
        cmake_info=parse_cmake_file(cmake_path),
        has_pyproject_toml=pyproject_path.exists(),
        pyproject_info=parse_pyproject(pyproject_path),
    )
