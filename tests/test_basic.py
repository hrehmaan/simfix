from pathlib import Path

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.cmake import parse_cmake_file
from simfix.compatibility import generate_compatibility_warnings
from simfix.conda_environment import parse_conda_environment
from simfix.dockerfile import parse_dockerfile
from simfix.planner import create_install_plan
from simfix.pypi import normalize_requirement_name
from simfix.python_requirements import parse_requirements_file
from simfix.repo import is_git_url, repo_name_from_url
from simfix.ros_package import parse_ros_package
from simfix.system import SystemInfo, command_exists, get_system_info


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
        git_available=True,
        docker_available=False,
        nvidia_gpu_available=False,
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
        git_available=True,
        docker_available=True,
        nvidia_gpu_available=False,
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
