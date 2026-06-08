from pathlib import Path

from simfix import __version__
from simfix.analyzer import analyze_repo


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_analyze_python_repo(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("numpy\n", encoding="utf-8")

    analysis = analyze_repo(tmp_path)

    assert analysis.has_requirements_txt is True
    assert analysis.has_pyproject_toml is False
    assert analysis.detected_ecosystems == ["python"]


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
