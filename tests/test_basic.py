from pathlib import Path

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.compatibility import generate_compatibility_warnings
from simfix.planner import create_install_plan
from simfix.pypi import normalize_requirement_name
from simfix.python_requirements import parse_requirements_file
from simfix.repo import is_git_url, repo_name_from_url
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
