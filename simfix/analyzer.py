from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simfix.cmake import CMakeInfo, parse_cmake_file
from simfix.conda_environment import CondaEnvironment, parse_conda_environment
from simfix.dockerfile import DockerfileInfo, parse_dockerfile
from simfix.pypi import normalize_requirement_name
from simfix.pyproject import PyProjectInfo, parse_pyproject
from simfix.python_requirements import parse_requirements_file
from simfix.ros_package import ROSPackageInfo, parse_ros_package
from simfix.dependency_discovery import discover_dependency_files
from simfix.setup_py import parse_setup_py_dependencies


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
    has_setup_py: bool
    setup_py_dependencies: list[str]
    python_requirements: list[str]
    conda_environment: CondaEnvironment | None
    dockerfile_info: DockerfileInfo | None
    ros_package_info: ROSPackageInfo | None
    cmake_info: CMakeInfo | None
    pyproject_info: PyProjectInfo | None

    @property
    def all_python_dependencies(self) -> list[str]:
        """Return all Python dependencies from supported dependency files."""
        dependencies = list(self.python_requirements)

        if self.pyproject_info is not None:
            dependencies.extend(self.pyproject_info.dependencies)

        dependencies.extend(self.setup_py_dependencies)

        unique_dependencies: dict[str, str] = {}

        for dependency in dependencies:
            package_name = normalize_requirement_name(dependency).lower()

            if package_name not in unique_dependencies:
                unique_dependencies[package_name] = dependency

        return list(unique_dependencies.values())

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

    discovered_files = discover_dependency_files(path)

    requirements_path = (
        discovered_files.requirements_txt[0]
        if discovered_files.requirements_txt
        else path / "requirements.txt"
    )
    environment_path = (
        discovered_files.environment_files[0]
        if discovered_files.environment_files
        else path / "environment.yml"
    )
    dockerfile_path = (
        discovered_files.dockerfiles[0]
        if discovered_files.dockerfiles
        else path / "Dockerfile"
    )
    package_xml_path = (
        discovered_files.package_xml_files[0]
        if discovered_files.package_xml_files
        else path / "package.xml"
    )
    cmake_path = (
        discovered_files.cmake_lists_files[0]
        if discovered_files.cmake_lists_files
        else path / "CMakeLists.txt"
    )
    pyproject_path = (
        discovered_files.pyproject_toml[0]
        if discovered_files.pyproject_toml
        else path / "pyproject.toml"
    )
    setup_py_path = (
        discovered_files.setup_py_files[0]
        if discovered_files.setup_py_files
        else path / "setup.py"
    )

    setup_py_dependencies = parse_setup_py_dependencies(setup_py_path)

    return RepoAnalysis(
        repo_path=path,
        has_requirements_txt=discovered_files.has_requirements_txt,
        has_environment_yml=discovered_files.has_environment_file,
        python_requirements=parse_requirements_file(requirements_path),
        conda_environment=parse_conda_environment(environment_path),
        has_dockerfile=discovered_files.has_dockerfile,
        dockerfile_info=parse_dockerfile(dockerfile_path),
        has_package_xml=discovered_files.has_ros_package,
        ros_package_info=parse_ros_package(package_xml_path),
        has_cmake=discovered_files.has_cmake_lists,
        cmake_info=parse_cmake_file(cmake_path),
        has_pyproject_toml=discovered_files.has_pyproject_toml,
        pyproject_info=parse_pyproject(pyproject_path),
        has_setup_py=discovered_files.has_setup_py,
        setup_py_dependencies=setup_py_dependencies,
    )
