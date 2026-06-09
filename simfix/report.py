from __future__ import annotations

from pathlib import Path

from simfix.analyzer import RepoAnalysis
from simfix.compatibility import generate_compatibility_warnings
from simfix.planner import InstallPlan
from simfix.system import SystemInfo


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def generate_markdown_report(
    analysis: RepoAnalysis,
    install_plan: InstallPlan,
    system_info: SystemInfo,
) -> str:
    """Generate a Markdown report from SimFix analysis results."""
    warnings = generate_compatibility_warnings(analysis, system_info)

    lines: list[str] = [
        "# SimFix Report",
        "",
        "## Repository",
        "",
        f"- Path: `{analysis.repo_path}`",
        f"- Detected ecosystem(s): `{', '.join(analysis.detected_ecosystems)}`",
        "",
        "## Detected dependency files",
        "",
        f"- `requirements.txt`: {_yes_no(analysis.has_requirements_txt)}",
        f"- `pyproject.toml`: {_yes_no(analysis.has_pyproject_toml)}",
        f"- `environment.yml`: {_yes_no(analysis.has_environment_yml)}",
        f"- `Dockerfile`: {_yes_no(analysis.has_dockerfile)}",
        f"- `package.xml`: {_yes_no(analysis.has_package_xml)}",
        f"- `CMakeLists.txt`: {_yes_no(analysis.has_cmake)}",
        "",
        "## System",
        "",
        f"- OS: `{system_info.os_name}`",
        f"- OS version: `{system_info.os_version}`",
        f"- Linux distro: `{system_info.linux_distro or '-'}`",
        f"- Linux version: `{system_info.linux_version or '-'}`",
        f"- WSL: `{_yes_no(system_info.is_wsl)}`",
        f"- Architecture: `{system_info.architecture}`",
        f"- Python: `{system_info.python_version}`",
        f"- Git: `{_yes_no(system_info.git_available)}`",
        f"- Docker: `{_yes_no(system_info.docker_available)}`",
        f"- NVIDIA GPU: `{_yes_no(system_info.nvidia_gpu_available)}`",
        f"- Pip: `{_yes_no(system_info.pip_available)}`",
        f"- Uv: `{_yes_no(system_info.uv_available)}`",
        f"- Conda: `{_yes_no(system_info.conda_available)}`",
        f"- Mamba: `{_yes_no(system_info.mamba_available)}`",
        "",
        "## Install plan",
        "",
        f"- Recommended mode: `{install_plan.recommended_mode}`",
        f"- Reason: {install_plan.reason}",
        "",
        "### Steps",
        "",
    ]

    lines.extend(f"{index}. {step}" for index, step in enumerate(install_plan.steps, 1))

    python_dependencies = analysis.all_python_dependencies

    if python_dependencies:
        lines.extend(
            [
                "",
                "## Python requirements",
                "",
            ]
        )
        lines.extend(f"- `{dependency}`" for dependency in python_dependencies)

    if analysis.pyproject_info is not None:
        pyproject_info = analysis.pyproject_info
        lines.extend(
            [
                "",
                "## PyProject",
                "",
                f"- Project name: `{pyproject_info.project_name or '-'}`",
                "",
                "### Dependencies",
                "",
            ]
        )
        lines.extend(f"- `{dependency}`" for dependency in python_dependencies)

        lines.extend(["", "### Build system requires", ""])
        lines.extend(
            f"- `{dependency}`" for dependency in pyproject_info.build_system_requires
        )

        if pyproject_info.optional_dependencies:
            lines.extend(["", "### Optional dependencies", ""])
            for group, dependencies in pyproject_info.optional_dependencies.items():
                lines.append(f"- `{group}`: {', '.join(dependencies)}")

    if analysis.conda_environment is not None:
        conda_env = analysis.conda_environment
        lines.extend(
            [
                "",
                "## Conda environment",
                "",
                f"- Name: `{conda_env.name or '-'}`",
                "",
                "### Conda packages",
                "",
            ]
        )
        lines.extend(f"- `{dependency}`" for dependency in conda_env.conda_dependencies)
        lines.extend(["", "### Pip packages", ""])
        lines.extend(f"- `{dependency}`" for dependency in conda_env.pip_dependencies)

    if analysis.dockerfile_info is not None:
        docker_info = analysis.dockerfile_info
        lines.extend(
            [
                "",
                "## Dockerfile",
                "",
                "### Base images",
                "",
            ]
        )
        lines.extend(f"- `{image}`" for image in docker_info.base_images)
        lines.extend(["", "### Apt packages", ""])
        lines.extend(f"- `{package}`" for package in docker_info.apt_packages)
        lines.extend(["", "### Pip packages", ""])
        lines.extend(f"- `{package}`" for package in docker_info.pip_packages)

    if analysis.ros_package_info is not None:
        ros_info = analysis.ros_package_info
        lines.extend(
            [
                "",
                "## ROS package",
                "",
                f"- Name: `{ros_info.name or '-'}`",
                "",
                "### Dependencies",
                "",
            ]
        )
        lines.extend(f"- `{dependency}`" for dependency in ros_info.all_dependencies)

    if analysis.cmake_info is not None:
        cmake_info = analysis.cmake_info
        lines.extend(
            [
                "",
                "## CMake",
                "",
                f"- Project name: `{cmake_info.project_name or '-'}`",
                f"- Minimum version: `{cmake_info.minimum_version or '-'}`",
                "",
                "### Found packages",
                "",
            ]
        )
        lines.extend(f"- `{package}`" for package in cmake_info.found_packages)

    if warnings:
        lines.extend(["", "## Compatibility warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.append("")

    return "\n".join(lines)


def write_markdown_report(
    report_text: str,
    output_path: str | Path = "simfix_report.md",
) -> Path:
    """Write a Markdown report to disk."""
    path = Path(output_path).expanduser().resolve()
    path.write_text(report_text, encoding="utf-8")
    return path
