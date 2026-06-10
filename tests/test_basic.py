from pathlib import Path

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.cmake import parse_cmake_file
from simfix.commands import create_command_plan
from simfix.compatibility import generate_compatibility_warnings
from simfix.conda_environment import parse_conda_environment
from simfix.conda_fixer import fix_conda_environment_file
from simfix.cuda_docker import create_cuda_dockerfile, detect_gpu_project
from simfix.docker_runner import create_docker_run_helper
from simfix.dockerfile import parse_dockerfile
from simfix.recommendations import generate_recommendations

from simfix.vendor_dependencies import detect_vendor_dependency_recommendations
from simfix.system_capabilities import SystemCapabilities
from simfix.fixer import (
    extract_direct_pin_conflict,
    fix_pyproject_with_uv,
    fix_requirements_with_uv,
    normalize_pip_requirement_syntax,
    remove_direct_requirement_pin,
)
from simfix.git_assets import fix_git_assets
from simfix.planner import create_install_plan
from simfix.pypi import normalize_requirement_name
from simfix.pyproject import parse_pyproject
from simfix.python_requirements import parse_requirements_file
from simfix.repo import is_git_url, repo_name_from_url
from simfix.report import generate_markdown_report, write_markdown_report
from simfix.ros_docker import create_ros_dockerfile
from simfix.ros_package import parse_ros_package
from simfix.setup_py import parse_setup_py_dependencies
from simfix.ros_environment import (
    RosEnvironmentInfo,
    detect_ros_environment_info,
)
from simfix.cuda import (
    CudaVersionInfo,
    _detect_cuda_version_from_text,
    _parse_nvidia_smi_cuda_version,
    is_cuda_version_mismatch,
)

from typer.testing import CliRunner

from simfix.cli import app

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
    assert __version__ == "0.1.4"


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

    assert command_plan.title == "Suggested installation commands"
    assert "python -m venv .venv" in command_plan.commands
    assert "source .venv/bin/activate" in command_plan.commands
    assert "python -m pip install -r requirements.txt" in command_plan.commands


def test_create_docker_command_plan(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)
    command_plan = create_command_plan(analysis)

    assert command_plan.title == "Suggested installation commands"
    assert any(
        command.startswith("docker build -t ") for command in command_plan.commands
    )
    assert any(
        command.startswith("docker run --rm -it ") for command in command_plan.commands
    )


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


def test_fix_conda_environment_file_updates_in_place(tmp_path: Path) -> None:
    environment_path = tmp_path / "environment.yml"
    environment_path.write_text(
        """
name: simulator
channels:
  - conda-forge
dependencies:
  - python=3.10
  - numpy
  - scipy
  - numpy>=1.26
  - pip
  - pip:
      - matplotlib
      - matplotlib>=3.8
""",
        encoding="utf-8",
    )

    result = fix_conda_environment_file(tmp_path)

    assert result is not None
    assert result.changed is True

    fixed_text = environment_path.read_text(encoding="utf-8")

    assert "numpy>=1.26" in fixed_text
    assert "matplotlib>=3.8" in fixed_text
    assert fixed_text.count("numpy") == 1
    assert fixed_text.count("matplotlib") == 1


def test_fix_conda_environment_file_returns_none_without_environment(
    tmp_path: Path,
) -> None:
    result = fix_conda_environment_file(tmp_path)

    assert result is None


def test_detect_gpu_project_from_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "torch\nnumpy\n",
        encoding="utf-8",
    )

    assert detect_gpu_project(tmp_path) is True


def test_detect_gpu_project_from_cuda_file(tmp_path: Path) -> None:
    (tmp_path / "kernel.cu").write_text(
        "__global__ void test_kernel() {}\n",
        encoding="utf-8",
    )

    assert detect_gpu_project(tmp_path) is True


def test_create_cuda_dockerfile_does_not_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "requirements.txt").write_text(
        "torch\n",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        "FROM ubuntu:22.04\n",
        encoding="utf-8",
    )

    result = create_cuda_dockerfile(tmp_path)

    assert result is not None
    assert result.changed is False
    assert result.file_path.read_text(encoding="utf-8") == "FROM ubuntu:22.04\n"


def test_create_cuda_dockerfile(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text(
        "torch\nnumpy\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "simfix.cuda_docker.get_system_info",
        lambda: SystemInfo(
            os_name="Linux",
            os_version="test",
            linux_distro="Ubuntu",
            linux_version="22.04",
            is_wsl=False,
            architecture="x86_64",
            python_version="3.12",
            git_available=True,
            docker_available=True,
            nvidia_gpu_available=True,
            nvidia_driver_version="550.54",
            nvidia_cuda_version="12.4",
            cuda_toolkit_version="12.4",
            pip_available=True,
            uv_available=True,
            conda_available=False,
            mamba_available=False,
        ),
    )

    result = create_cuda_dockerfile(tmp_path)

    assert result is not None
    assert result.changed is True
    assert result.file_path.name == "Dockerfile"
    assert "NVIDIA GPU detected" in result.message

    dockerfile_text = result.file_path.read_text(encoding="utf-8")
    assert "nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04" in dockerfile_text
    assert "python3 -m pip install -r /workspace/requirements.txt" in dockerfile_text


def test_fix_git_assets_returns_none_for_non_git_repo(tmp_path: Path) -> None:
    result = fix_git_assets(tmp_path)

    assert result is None


def test_fix_git_assets_reports_missing_git_lfs(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitattributes").write_text(
        "*.bin filter=lfs diff=lfs merge=lfs -text\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "simfix.git_assets._command_exists", lambda command: command == "git"
    )
    monkeypatch.setattr("simfix.git_assets._is_git_repo", lambda path: True)

    result = fix_git_assets(tmp_path)

    assert result is not None
    assert result.changed is False
    assert "Git LFS files detected" in result.message


def test_fix_git_assets_updates_submodules(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitmodules").write_text(
        """
[submodule "external/test"]
    path = external/test
    url = https://example.com/test.git
""",
        encoding="utf-8",
    )

    class FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("simfix.git_assets._command_exists", lambda command: True)
    monkeypatch.setattr("simfix.git_assets._is_git_repo", lambda path: True)
    monkeypatch.setattr(
        "simfix.git_assets._run_command",
        lambda command, cwd: FakeResult(),
    )

    result = fix_git_assets(tmp_path)

    assert result is not None
    assert result.changed is True
    assert "Git submodules updated successfully" in result.message


def test_create_docker_run_helper(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM ubuntu:22.04\n",
        encoding="utf-8",
    )

    result = create_docker_run_helper(tmp_path)

    assert result is not None
    assert result.changed is True
    assert result.file_path.name == "run_simfix_docker.sh"

    script_text = result.file_path.read_text(encoding="utf-8")
    assert "docker build" in script_text
    assert "docker run" in script_text
    assert "--gpus all" not in script_text


def test_create_docker_run_helper_with_gpu(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "torch\n",
        encoding="utf-8",
    )

    result = create_docker_run_helper(tmp_path)

    assert result is not None
    assert result.changed is True

    script_text = result.file_path.read_text(encoding="utf-8")
    assert "--gpus all" in script_text


def test_create_docker_run_helper_does_not_overwrite_existing_script(
    tmp_path: Path,
) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM ubuntu:22.04\n",
        encoding="utf-8",
    )
    (tmp_path / "run_simfix_docker.sh").write_text(
        "# existing script\n",
        encoding="utf-8",
    )

    result = create_docker_run_helper(tmp_path)

    assert result is not None
    assert result.changed is False
    assert result.file_path.read_text(encoding="utf-8") == "# existing script\n"


def test_fix_pyproject_with_uv_returns_none_without_pyproject(
    tmp_path: Path,
) -> None:
    result = fix_pyproject_with_uv(tmp_path)

    assert result is None


def test_fix_pyproject_with_uv_skips_when_requirements_exists(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example"
version = "0.1.0"
dependencies = [
    "numpy",
]
""",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    result = fix_pyproject_with_uv(tmp_path)

    assert result is None


def test_fix_pyproject_with_uv_reports_missing_uv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example"
version = "0.1.0"
dependencies = [
    "numpy",
]
""",
        encoding="utf-8",
    )

    monkeypatch.setattr("simfix.fixer._command_exists", lambda command: False)

    result = fix_pyproject_with_uv(tmp_path)

    assert result is not None
    assert result.changed is False
    assert "uv was not found" in result.message


def test_parse_setup_py_dependencies(tmp_path: Path) -> None:
    setup_py_path = tmp_path / "setup.py"
    setup_py_path.write_text(
        """
from setuptools import setup

setup(
    name="example",
    install_requires=[
        "isaacgym",
        "numpy==1.23",
        "torch",
    ],
)
""",
        encoding="utf-8",
    )

    dependencies = parse_setup_py_dependencies(setup_py_path)

    assert dependencies == ["isaacgym", "numpy==1.23", "torch"]


def test_analyze_repo_detects_setup_py_dependencies(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        """
from setuptools import setup

setup(
    name="example",
    install_requires=[
        "isaacgym",
        "torch",
    ],
)
""",
        encoding="utf-8",
    )

    analysis = analyze_repo(tmp_path)

    assert analysis.has_setup_py is True
    assert analysis.setup_py_dependencies == ["isaacgym", "torch"]
    assert "isaacgym" in analysis.all_python_dependencies
    assert "torch" in analysis.all_python_dependencies


def test_normalize_pip_requirement_syntax_converts_single_equals() -> None:
    text = "numpy>=1.23\nurdfpy=0.0.22\nscipy\n"

    normalized = normalize_pip_requirement_syntax(text)

    assert normalized == "numpy>=1.23\nurdfpy==0.0.22\nscipy\n"


def test_parse_dockerfile_ignores_requirements_file_pip_install(
    tmp_path: Path,
) -> None:
    dockerfile_path = tmp_path / "Dockerfile"
    dockerfile_path.write_text(
        """
FROM ubuntu:22.04

RUN python3 -m pip install --upgrade pip && \\
    python3 -m pip install -r /workspace/requirements.txt
""",
        encoding="utf-8",
    )

    info = parse_dockerfile(dockerfile_path)

    assert info is not None
    assert info.pip_packages == []


def test_extract_direct_pin_conflict() -> None:
    error_text = (
        "Because urdfpy==0.0.22 depends on networkx==2.2 and "
        "you require urdfpy==0.0.22, we can conclude that you "
        "require networkx==2.2. And because you require "
        "networkx==3.1, we can conclude that your requirements "
        "are unsatisfiable."
    )

    conflict = extract_direct_pin_conflict(error_text)

    assert conflict == "networkx"


def test_remove_direct_requirement_pin() -> None:
    requirements_text = "urdfpy==0.0.22\n" "networkx==3.1\n" "numpy==1.23\n"

    fixed_text = remove_direct_requirement_pin(
        requirements_text,
        "networkx",
    )

    assert fixed_text == "urdfpy==0.0.22\nnumpy==1.23\n"


def test_generate_recommendations_detects_isaacgym() -> None:
    recommendations = generate_recommendations(
        dependencies=["isaacgym", "torch"],
        detected_ecosystems=["python"],
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "NVIDIA Isaac Gym required" in titles
    assert "CUDA-compatible environment recommended" in titles


def test_generate_recommendations_detects_isaacsim() -> None:
    recommendations = generate_recommendations(
        dependencies=["omni.isaac.core"],
        detected_ecosystems=["python"],
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "NVIDIA Isaac Sim required" in titles
    assert "CUDA-compatible environment recommended" in titles


def test_generate_recommendations_detects_ros() -> None:
    recommendations = generate_recommendations(
        dependencies=[],
        detected_ecosystems=["ros"],
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "ROS environment required" in titles


def test_generate_recommendations_empty_for_simple_python_project() -> None:
    recommendations = generate_recommendations(
        dependencies=["numpy", "matplotlib"],
        detected_ecosystems=["python"],
    )

    assert recommendations == []


def test_recommendations_command_simple_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["recommendations", str(repo)])

    assert result.exit_code == 0
    assert "SimFix Recommendations" in result.output


def test_recommendations_command_detects_isaacgym(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("isaacgym\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["recommendations", str(repo)])

    assert result.exit_code == 0
    assert "SimFix Recommendations" in result.output


def test_vendor_dependency_recommendations_detect_isaacgym() -> None:
    recommendations = detect_vendor_dependency_recommendations(["isaacgym"])

    titles = [recommendation.title for recommendation in recommendations]

    assert "NVIDIA Isaac Gym required" in titles


def test_doctor_shows_recommendations_hint_for_vendor_dependency(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("isaacgym\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["doctor", str(repo)])

    assert result.exit_code == 0
    assert "System/vendor recommendations found" in result.output
    assert "simfix recommendations" in result.output


def test_doctor_does_not_show_recommendations_hint_for_simple_repo(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["doctor", str(repo)])

    assert result.exit_code == 0
    assert "System/vendor recommendations found" not in result.output


def test_recommendations_warn_for_old_dependencies_on_new_python() -> None:
    recommendations = generate_recommendations(
        dependencies=[
            "numpy==1.23.0",
            "networkx==2.2",
            "urdfpy==0.0.22",
        ],
        detected_ecosystems=["python"],
        python_version=(3, 13),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "Older pinned dependencies detected" in titles


def test_recommendations_do_not_warn_for_old_dependencies_on_python_310() -> None:
    recommendations = generate_recommendations(
        dependencies=[
            "numpy==1.23.0",
            "networkx==2.2",
            "urdfpy==0.0.22",
        ],
        detected_ecosystems=["python"],
        python_version=(3, 10),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "Older pinned dependencies detected" not in titles


def test_recommendations_warn_when_gpu_docker_runtime_missing() -> None:
    recommendations = generate_recommendations(
        dependencies=["cupy-cuda12x", "torch"],
        detected_ecosystems=["python"],
        system_capabilities=SystemCapabilities(
            has_docker=True,
            has_nvidia_smi=True,
            has_nvidia_container_runtime=False,
        ),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "NVIDIA Docker support not detected" in titles


def test_recommendations_do_not_warn_when_gpu_docker_runtime_exists() -> None:
    recommendations = generate_recommendations(
        dependencies=["cupy-cuda12x", "torch"],
        detected_ecosystems=["python"],
        system_capabilities=SystemCapabilities(
            has_docker=True,
            has_nvidia_smi=True,
            has_nvidia_container_runtime=True,
        ),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "NVIDIA Docker support not detected" not in titles


def test_detect_cuda_version_from_nvidia_docker_image() -> None:
    text = "FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04"

    assert _detect_cuda_version_from_text(text) == (12, 4)


def test_detect_cuda_version_from_compact_dependency() -> None:
    text = "cupy-cuda12x\nsome-package-cu118"

    assert _detect_cuda_version_from_text(text) == (12, 0)


def test_parse_nvidia_smi_cuda_version() -> None:
    text = "NVIDIA-SMI 535.104.05    Driver Version: 535.104.05    CUDA Version: 12.2"

    assert _parse_nvidia_smi_cuda_version(text) == (12, 2)


def test_cuda_version_mismatch_detected() -> None:
    assert is_cuda_version_mismatch((12, 4), (12, 2))


def test_cuda_version_mismatch_not_detected_when_system_is_newer() -> None:
    assert not is_cuda_version_mismatch((12, 1), (12, 4))


def test_recommendations_warn_for_cuda_version_mismatch() -> None:
    recommendations = generate_recommendations(
        dependencies=["cupy-cuda12x"],
        detected_ecosystems=["python"],
        cuda_version_info=CudaVersionInfo(
            repo_cuda_version=(12, 4),
            system_cuda_version=(12, 2),
            repo_cuda_source="Dockerfile",
        ),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "CUDA version mismatch detected" in titles


def test_recommendations_warn_when_repo_cuda_known_but_system_cuda_unknown() -> None:
    recommendations = generate_recommendations(
        dependencies=[],
        detected_ecosystems=["docker"],
        cuda_version_info=CudaVersionInfo(
            repo_cuda_version=(12, 4),
            system_cuda_version=None,
            repo_cuda_source="Dockerfile",
        ),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "System CUDA support not detected" in titles


def test_detect_ros1_catkin_environment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "package.xml").write_text(
        """
        <package format="2">
          <name>test_ros1_package</name>
          <buildtool_depend>catkin</buildtool_depend>
          <depend>roscpp</depend>
        </package>
        """,
        encoding="utf-8",
    )

    info = detect_ros_environment_info(repo)

    assert info is not None
    assert info.project_type == "ROS 1 / catkin"
    assert info.recommended_distribution == "Noetic"
    assert info.recommended_ubuntu == "Ubuntu 20.04"
    assert info.recommended_docker_image == "osrf/ros:noetic-desktop-full"


def test_detect_ros2_ament_environment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "package.xml").write_text(
        """
        <package format="3">
          <name>test_ros2_package</name>
          <buildtool_depend>ament_cmake</buildtool_depend>
          <depend>rclcpp</depend>
        </package>
        """,
        encoding="utf-8",
    )

    info = detect_ros_environment_info(repo)

    assert info is not None
    assert info.project_type == "ROS 2 / ament"
    assert info.recommended_distribution == "Humble"
    assert info.recommended_ubuntu == "Ubuntu 22.04"
    assert info.recommended_docker_image == "osrf/ros:humble-desktop"


def test_recommendations_include_ros_environment_info() -> None:
    recommendations = generate_recommendations(
        dependencies=[],
        detected_ecosystems=["ros"],
        ros_environment_info=RosEnvironmentInfo(
            project_type="ROS 1 / catkin",
            recommended_distribution="Noetic",
            recommended_ubuntu="Ubuntu 20.04",
            recommended_docker_image="osrf/ros:noetic-desktop-full",
            source="package.xml",
        ),
    )

    titles = [recommendation.title for recommendation in recommendations]

    assert "ROS 1 / catkin environment detected" in titles


def test_vendor_dependency_recommendations_detect_mujoco_py() -> None:
    recommendations = detect_vendor_dependency_recommendations(["mujoco-py"])

    titles = [recommendation.title for recommendation in recommendations]

    assert "MuJoCo system dependencies may be required" in titles


def test_vendor_dependency_recommendations_detect_gpu_runtime() -> None:
    recommendations = detect_vendor_dependency_recommendations(["onnxruntime-gpu"])

    titles = [recommendation.title for recommendation in recommendations]

    assert "CUDA runtime compatibility check recommended" in titles


def test_vendor_dependency_recommendations_ignore_normal_python_packages() -> None:
    recommendations = detect_vendor_dependency_recommendations(["numpy", "matplotlib"])

    assert recommendations == []


def test_detect_ros_environment_info_from_nested_workspace(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    package = repo / "planner_gazebo_sim"
    package.mkdir(parents=True)

    (package / "package.xml").write_text(
        """
        <package format="2">
          <name>planner_gazebo_sim</name>
          <buildtool_depend>catkin</buildtool_depend>
          <depend>roscpp</depend>
        </package>
        """,
        encoding="utf-8",
    )
    (package / "CMakeLists.txt").write_text(
        "find_package(catkin REQUIRED)",
        encoding="utf-8",
    )

    info = detect_ros_environment_info(repo)

    assert info is not None
    assert info.project_type == "ROS 1 / catkin"
    assert info.recommended_distribution == "Noetic"
    assert info.recommended_ubuntu == "Ubuntu 20.04"
