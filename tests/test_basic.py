from pathlib import Path

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.cmake import parse_cmake_file
from simfix.commands import create_command_plan
from simfix.compatibility import generate_compatibility_warnings
from simfix.conda_environment import parse_conda_environment
from simfix.dockerfile import parse_dockerfile
from simfix.fixer import fix_requirements_with_uv
from simfix.planner import create_install_plan
from simfix.pypi import normalize_requirement_name
from simfix.pyproject import parse_pyproject
from simfix.python_requirements import parse_requirements_file
from simfix.repo import is_git_url, repo_name_from_url
from simfix.report import generate_markdown_report, write_markdown_report
from simfix.ros_docker import create_ros_dockerfile
from simfix.ros_package import parse_ros_package
from simfix.system import (
    SystemInfo,
    command_exists,
    get_cuda_toolkit_version,
    get_linux_os_release,
    get_nvidia_smi_field,
    get_system_info,
    is_windows_subsystem_for_linux,
)


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_analyze_python_repo(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)

    assert analysis.has_requirements_txt is True
    assert analysis.has_pyproject_toml is False
    assert analysis.detected_ecosystems == ["python"]
    assert analysis.python_requirements == ["numpy"]


def test_analyze_ros_cmake_repo(tmp_path: Path) -> None:
    (tmp_path / "package.xml").write_text("<package></package>\n", encoding="utf-8")
    (tmp_path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.10)\n", encoding="utf-8"
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_package_xml is True
    assert analysis.has_cmake is True
    assert "ros" in analysis.detected_ecosystems
    assert "cmake/c++" in analysis.detected_ecosystems


def test_is_git_url() -> None:
    assert is_git_url("https://github.com/hrehmaan/simfix.git") is True
    assert is_git_url("../simfix_test") is False


def test_repo_name_from_url() -> None:
    assert repo_name_from_url("https://github.com/hrehmaan/simfix.git") == "simfix"
    assert repo_name_from_url("https://github.com/hrehmaan/simfix") == "simfix"


def test_parse_requirements_file(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        """
# Core dependencies
numpy>=1.26
matplotlib==3.8.0

-r extra-requirements.txt
-e .
--index-url https://example.com/simple
scipy  # numerical package
""",
        encoding="utf-8",
    )

    dependencies = parse_requirements_file(requirements)

    assert dependencies == [
        "numpy>=1.26",
        "matplotlib==3.8.0",
        "scipy",
    ]


def test_normalize_requirement_name() -> None:
    assert normalize_requirement_name("numpy>=1.26") == "numpy"
    assert normalize_requirement_name("matplotlib==3.8.0") == "matplotlib"
    assert normalize_requirement_name("scipy") == "scipy"
    assert normalize_requirement_name("pandas!=2.0") == "pandas"


def test_create_python_install_plan(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    plan = create_install_plan(analysis)

    assert plan.recommended_mode == "python"
    assert "Python" in plan.reason


def test_create_docker_install_plan(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    plan = create_install_plan(analysis)

    assert plan.recommended_mode == "docker"
    assert "Dockerfile" in plan.reason


def test_command_exists_for_python() -> None:
    assert command_exists("python") or command_exists("python3")


def test_get_system_info() -> None:
    info = get_system_info()

    assert info.os_name
    assert info.architecture
    assert info.python_version


def test_docker_warning_when_docker_missing(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    system_info = SystemInfo(
        os_name="Linux",
        os_version="test",
        architecture="x86_64",
        python_version="3.12",
        linux_distro="Ubuntu",
        linux_version="22.04",
        is_wsl=False,
        git_available=True,
        docker_available=False,
        nvidia_gpu_available=False,
        nvidia_driver_version=None,
        nvidia_cuda_version=None,
        cuda_toolkit_version=None,
        pip_available=True,
        uv_available=False,
        conda_available=False,
        mamba_available=False,
    )

    warnings = generate_compatibility_warnings(analysis, system_info)

    assert warnings == ["Dockerfile detected, but Docker was not found on this system."]


def test_ros_warning_on_macos(tmp_path: Path) -> None:
    (tmp_path / "package.xml").write_text("<package></package>\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    system_info = SystemInfo(
        os_name="Darwin",
        os_version="test",
        architecture="arm64",
        python_version="3.12",
        linux_distro="Ubuntu",
        linux_version="22.04",
        is_wsl=False,
        git_available=True,
        docker_available=True,
        nvidia_gpu_available=False,
        nvidia_driver_version=None,
        nvidia_cuda_version=None,
        cuda_toolkit_version=None,
        pip_available=True,
        uv_available=False,
        conda_available=False,
        mamba_available=False,
    )

    warnings = generate_compatibility_warnings(analysis, system_info)

    assert any("ROS project detected" in warning for warning in warnings)


def test_parse_conda_environment(tmp_path: Path) -> None:
    environment = tmp_path / "environment.yml"
    environment.write_text(
        """
name: sim-env
channels:
  - conda-forge
dependencies:
  - python=3.10
  - numpy
  - scipy
  - pip
  - pip:
      - typer>=0.12
      - rich
""",
        encoding="utf-8",
    )

    conda_env = parse_conda_environment(environment)

    assert conda_env is not None
    assert conda_env.name == "sim-env"
    assert conda_env.conda_dependencies == [
        "python=3.10",
        "numpy",
        "scipy",
        "pip",
    ]
    assert conda_env.pip_dependencies == [
        "typer>=0.12",
        "rich",
    ]


def test_analyze_conda_repo(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        """
name: sim-env
dependencies:
  - python=3.10
  - numpy
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_environment_yml is True
    assert "conda" in analysis.detected_ecosystems
    assert analysis.conda_environment is not None
    assert analysis.conda_environment.name == "sim-env"


def test_parse_dockerfile(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        """
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \\
    git \\
    cmake \\
    build-essential

RUN python -m pip install numpy scipy
""",
        encoding="utf-8",
    )

    info = parse_dockerfile(dockerfile)

    assert info is not None
    assert info.base_images == ["ubuntu:22.04"]
    assert "git" in info.apt_packages
    assert "cmake" in info.apt_packages
    assert "build-essential" in info.apt_packages
    assert "numpy" in info.pip_packages
    assert "scipy" in info.pip_packages


def test_analyze_docker_repo(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        """
FROM python:3.12

RUN pip install numpy
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_dockerfile is True
    assert "docker" in analysis.detected_ecosystems
    assert analysis.dockerfile_info is not None
    assert analysis.dockerfile_info.base_images == ["python:3.12"]
    assert analysis.dockerfile_info.pip_packages == ["numpy"]


def test_parse_ros_package(tmp_path: Path) -> None:
    package_xml = tmp_path / "package.xml"
    package_xml.write_text(
        """
<package format="2">
  <name>tiny_robot_sim</name>
  <version>0.1.0</version>
  <description>Tiny ROS simulator test package.</description>
  <maintainer email="test@example.com">Test User</maintainer>
  <license>MIT</license>

  <buildtool_depend>catkin</buildtool_depend>
  <build_depend>roscpp</build_depend>
  <build_depend>gazebo_ros</build_depend>
  <exec_depend>rospy</exec_depend>
  <exec_depend>std_msgs</exec_depend>
  <test_depend>rostest</test_depend>
</package>
""",
        encoding="utf-8",
    )

    info = parse_ros_package(package_xml)

    assert info is not None
    assert info.name == "tiny_robot_sim"
    assert info.build_tool_dependencies == ["catkin"]
    assert info.build_dependencies == ["roscpp", "gazebo_ros"]
    assert info.execution_dependencies == ["rospy", "std_msgs"]
    assert info.test_dependencies == ["rostest"]
    assert "gazebo_ros" in info.all_dependencies


def test_analyze_ros_package_repo(tmp_path: Path) -> None:
    (tmp_path / "package.xml").write_text(
        """
<package format="2">
  <name>tiny_robot_sim</name>
  <version>0.1.0</version>
  <description>Tiny ROS simulator test package.</description>
  <maintainer email="test@example.com">Test User</maintainer>
  <license>MIT</license>
  <buildtool_depend>catkin</buildtool_depend>
</package>
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_package_xml is True
    assert "ros" in analysis.detected_ecosystems
    assert analysis.ros_package_info is not None
    assert analysis.ros_package_info.name == "tiny_robot_sim"


def test_parse_cmake_file(tmp_path: Path) -> None:
    cmake_file = tmp_path / "CMakeLists.txt"
    cmake_file.write_text(
        """
cmake_minimum_required(VERSION 3.16)
project(tiny_simulator)

find_package(OpenGL REQUIRED)
find_package(SDL2 REQUIRED)
find_package(Freetype REQUIRED)
""",
        encoding="utf-8",
    )

    info = parse_cmake_file(cmake_file)

    assert info is not None
    assert info.minimum_version == "3.16"
    assert info.project_name == "tiny_simulator"
    assert info.found_packages == ["OpenGL", "SDL2", "Freetype"]


def test_analyze_cmake_repo(tmp_path: Path) -> None:
    (tmp_path / "CMakeLists.txt").write_text(
        """
cmake_minimum_required(VERSION 3.16)
project(tiny_simulator)
find_package(OpenGL REQUIRED)
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_cmake is True
    assert "cmake/c++" in analysis.detected_ecosystems
    assert analysis.cmake_info is not None
    assert analysis.cmake_info.project_name == "tiny_simulator"
    assert analysis.cmake_info.found_packages == ["OpenGL"]


def test_generate_markdown_report(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    install_plan = create_install_plan(analysis)
    system_info = SystemInfo(
        os_name="Linux",
        os_version="test",
        architecture="x86_64",
        python_version="3.12",
        linux_distro="Ubuntu",
        linux_version="22.04",
        is_wsl=False,
        git_available=True,
        docker_available=False,
        nvidia_gpu_available=False,
        nvidia_driver_version=None,
        nvidia_cuda_version=None,
        cuda_toolkit_version=None,
        pip_available=True,
        uv_available=False,
        conda_available=False,
        mamba_available=False,
    )

    report = generate_markdown_report(
        analysis=analysis,
        install_plan=install_plan,
        system_info=system_info,
    )

    assert "# SimFix Report" in report
    assert "requirements.txt" in report
    assert "numpy" in report
    assert "Recommended mode" in report


def test_write_markdown_report(tmp_path: Path) -> None:
    output_path = tmp_path / "simfix_report.md"

    written_path = write_markdown_report("hello\n", output_path)

    assert written_path == output_path.resolve()
    assert output_path.read_text(encoding="utf-8") == "hello\n"


def test_parse_pyproject_project_dependencies(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[build-system]
requires = ["setuptools>=68", "wheel"]

[project]
name = "tiny-sim"
dependencies = [
  "numpy>=1.26",
  "matplotlib",
]

[project.optional-dependencies]
dev = [
  "pytest",
  "ruff",
]
""",
        encoding="utf-8",
    )

    info = parse_pyproject(pyproject)

    assert info is not None
    assert info.project_name == "tiny-sim"
    assert info.dependencies == ["numpy>=1.26", "matplotlib"]
    assert info.optional_dependencies == {"dev": ["pytest", "ruff"]}
    assert info.build_system_requires == ["setuptools>=68", "wheel"]


def test_analyze_pyproject_repo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "tiny-sim"
dependencies = ["numpy"]
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_pyproject_toml is True
    assert "python" in analysis.detected_ecosystems
    assert analysis.pyproject_info is not None
    assert analysis.pyproject_info.project_name == "tiny-sim"
    assert analysis.pyproject_info.dependencies == ["numpy"]


def test_all_python_dependencies_combines_requirements_and_pyproject(
    tmp_path: Path,
) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "tiny-sim"
dependencies = ["matplotlib", "numpy"]
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.all_python_dependencies == ["numpy", "matplotlib"]


def test_conda_warning_when_conda_and_mamba_missing(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        """
name: sim-env
dependencies:
  - python=3.10
  - numpy
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)
    system_info = SystemInfo(
        os_name="Linux",
        os_version="test",
        architecture="x86_64",
        python_version="3.12",
        linux_distro="Ubuntu",
        linux_version="22.04",
        is_wsl=False,
        git_available=True,
        docker_available=True,
        nvidia_gpu_available=False,
        nvidia_driver_version=None,
        nvidia_cuda_version=None,
        cuda_toolkit_version=None,
        pip_available=True,
        uv_available=False,
        conda_available=False,
        mamba_available=False,
    )

    warnings = generate_compatibility_warnings(analysis, system_info)

    assert (
        "Conda environment detected, but neither conda nor mamba was found." in warnings
    )


def test_get_linux_os_release_returns_tuple() -> None:
    distro, version = get_linux_os_release()

    assert distro is None or isinstance(distro, str)
    assert version is None or isinstance(version, str)


def test_is_windows_subsystem_for_linux_returns_bool() -> None:
    assert isinstance(is_windows_subsystem_for_linux(), bool)


def test_ros_noetic_ubuntu_mismatch_warning(tmp_path: Path) -> None:
    (tmp_path / "package.xml").write_text(
        """
<package format="2">
  <name>tiny_robot_sim</name>
  <version>0.1.0</version>
  <description>Tiny ROS simulator test package.</description>
  <maintainer email="test@example.com">Test User</maintainer>
  <license>MIT</license>
  <buildtool_depend>catkin</buildtool_depend>
</package>
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)
    system_info = SystemInfo(
        os_name="Linux",
        os_version="test",
        linux_distro="Ubuntu",
        linux_version="22.04",
        is_wsl=False,
        architecture="x86_64",
        python_version="3.12",
        git_available=True,
        docker_available=True,
        nvidia_gpu_available=False,
        nvidia_driver_version=None,
        nvidia_cuda_version=None,
        cuda_toolkit_version=None,
        pip_available=True,
        uv_available=False,
        conda_available=False,
        mamba_available=False,
    )

    warnings = generate_compatibility_warnings(analysis, system_info)

    assert any("ROS noetic project detected" in warning for warning in warnings)


def test_get_nvidia_smi_field_returns_optional_string() -> None:
    value = get_nvidia_smi_field("driver_version")

    assert value is None or isinstance(value, str)


def test_get_cuda_toolkit_version_returns_optional_string() -> None:
    value = get_cuda_toolkit_version()

    assert value is None or isinstance(value, str)


def test_create_python_command_plan(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    command_plan = create_command_plan(analysis)

    assert command_plan.title == "Python installation commands"
    assert "python -m venv .venv" in command_plan.commands
    assert "python -m pip install -r requirements.txt" in command_plan.commands


def test_create_docker_command_plan(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    command_plan = create_command_plan(analysis)

    assert command_plan.title == "Docker installation commands"
    assert any("docker build" in command for command in command_plan.commands)


def test_fix_requirements_with_uv_returns_none_without_requirements(
    tmp_path: Path,
) -> None:
    result = fix_requirements_with_uv(tmp_path)

    assert result is None


def test_fix_requirements_with_uv_reports_missing_uv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    monkeypatch.setattr("simfix.fixer._command_exists", lambda command: False)

    result = fix_requirements_with_uv(tmp_path)

    assert result is not None
    assert result.changed is False
    assert "uv was not found" in result.message


def test_create_ros1_dockerfile(tmp_path: Path) -> None:
    (tmp_path / "package.xml").write_text(
        """
<package format="2">
  <name>test_ros_package</name>
  <version>0.1.0</version>
  <description>Test package</description>
  <maintainer email="test@example.com">Test</maintainer>
  <license>MIT</license>
  <buildtool_depend>catkin</buildtool_depend>
</package>
""",
        encoding="utf-8",
    )

    result = create_ros_dockerfile(tmp_path)

    assert result is not None
    assert result.changed is True
    assert result.file_path.name == "Dockerfile"

    dockerfile_text = result.file_path.read_text(encoding="utf-8")
    assert "osrf/ros:noetic-desktop-full" in dockerfile_text
    assert "catkin build" in dockerfile_text


def test_create_ros2_dockerfile(tmp_path: Path) -> None:
    (tmp_path / "package.xml").write_text(
        """
<package format="3">
  <name>test_ros2_package</name>
  <version>0.1.0</version>
  <description>Test package</description>
  <maintainer email="test@example.com">Test</maintainer>
  <license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
</package>
""",
        encoding="utf-8",
    )

    result = create_ros_dockerfile(tmp_path)

    assert result is not None
    assert result.changed is True
    assert result.file_path.name == "Dockerfile"

    dockerfile_text = result.file_path.read_text(encoding="utf-8")
    assert "osrf/ros:humble-desktop" in dockerfile_text
    assert "colcon build" in dockerfile_text


def test_create_ros_dockerfile_does_not_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.xml").write_text(
        """
<package format="2">
  <name>test_ros_package</name>
  <version>0.1.0</version>
  <description>Test package</description>
  <maintainer email="test@example.com">Test</maintainer>
  <license>MIT</license>
  <buildtool_depend>catkin</buildtool_depend>
</package>
""",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n", encoding="utf-8")

    result = create_ros_dockerfile(tmp_path)

    assert result is not None
    assert result.changed is False
    assert result.file_path.read_text(encoding="utf-8") == "FROM ubuntu:22.04\n"
