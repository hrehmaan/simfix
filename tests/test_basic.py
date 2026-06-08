from pathlib import Path

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.python_requirements import parse_requirements_file
from simfix.repo import is_git_url, repo_name_from_url


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
