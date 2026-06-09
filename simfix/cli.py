from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.compatibility import generate_compatibility_warnings
from simfix.planner import create_install_plan
from simfix.pypi import check_pypi_packages
from simfix.repo import clone_repo, is_git_url
from simfix.report import generate_markdown_report, write_markdown_report
from simfix.system import get_system_info

app = typer.Typer(
    name="simfix",
    help="Smart dependency checker and installer assistant for simulator repositories.",
)

console = Console()


def _resolve_repo_path(repo: str) -> Path:
    """Resolve a local path or clone a Git repository URL."""
    if is_git_url(repo):
        console.print("[bold blue]Cloning repository...[/bold blue]")
        return clone_repo(repo)

    return Path(repo)


@app.command()
def analyze(repo: str) -> None:
    """Analyze repository dependency files without system diagnostics."""
    repo_path = _resolve_repo_path(repo)
    analysis = analyze_repo(repo_path)

    console.print("[bold green]SimFix Analyze[/bold green]")
    console.print(f"Repository: {analysis.repo_path}")

    table = Table(title="Detected dependency files")
    table.add_column("File/type", style="cyan")
    table.add_column("Detected", style="green")

    table.add_row("requirements.txt", "yes" if analysis.has_requirements_txt else "no")
    table.add_row("pyproject.toml", "yes" if analysis.has_pyproject_toml else "no")
    table.add_row("environment.yml", "yes" if analysis.has_environment_yml else "no")
    table.add_row("Dockerfile", "yes" if analysis.has_dockerfile else "no")
    table.add_row("package.xml / ROS", "yes" if analysis.has_package_xml else "no")
    table.add_row("CMakeLists.txt", "yes" if analysis.has_cmake else "no")

    console.print(table)

    ecosystems = ", ".join(analysis.detected_ecosystems)
    console.print(f"[bold]Detected ecosystem(s):[/bold] {ecosystems}")


@app.command()
def plan(repo: str) -> None:
    """Generate a recommended installation plan for a repository."""
    repo_path = _resolve_repo_path(repo)
    analysis = analyze_repo(repo_path)
    install_plan = create_install_plan(analysis)

    console.print("[bold green]SimFix Plan[/bold green]")
    console.print(f"Repository: {analysis.repo_path}")

    ecosystems = ", ".join(analysis.detected_ecosystems)
    console.print(f"[bold]Detected ecosystem(s):[/bold] {ecosystems}")

    plan_table = Table(title="Install plan")
    plan_table.add_column("Field", style="cyan")
    plan_table.add_column("Value", style="green")

    plan_table.add_row("Recommended mode", install_plan.recommended_mode)
    plan_table.add_row("Reason", install_plan.reason)
    plan_table.add_row("Steps", "\n".join(install_plan.steps))

    console.print(plan_table)


@app.command()
def doctor(
    repo: str,
    report: bool = typer.Option(
        False,
        "--report",
        help="Write a Markdown SimFix report to simfix_report.md.",
    ),
) -> None:
    """Analyze a local path or Git repository URL."""
    repo_path = _resolve_repo_path(repo)

    analysis = analyze_repo(repo_path)
    system_info = get_system_info()

    console.print("[bold green]SimFix Doctor[/bold green]")
    console.print(f"Repository: {analysis.repo_path}")

    table = Table(title="Detected dependency files")
    table.add_column("File/type", style="cyan")
    table.add_column("Detected", style="green")

    table.add_row("requirements.txt", "yes" if analysis.has_requirements_txt else "no")
    table.add_row("pyproject.toml", "yes" if analysis.has_pyproject_toml else "no")
    table.add_row("environment.yml", "yes" if analysis.has_environment_yml else "no")
    table.add_row("Dockerfile", "yes" if analysis.has_dockerfile else "no")
    table.add_row("package.xml / ROS", "yes" if analysis.has_package_xml else "no")
    table.add_row("CMakeLists.txt", "yes" if analysis.has_cmake else "no")

    console.print(table)

    ecosystems = ", ".join(analysis.detected_ecosystems)
    console.print(f"[bold]Detected ecosystem(s):[/bold] {ecosystems}")

    python_dependencies = analysis.all_python_dependencies

    if python_dependencies:
        deps_table = Table(title="Python packages")
        deps_table.add_column("Dependency", style="cyan")

        for dependency in python_dependencies:
            deps_table.add_row(dependency)

        console.print(deps_table)

        pypi_results = check_pypi_packages(python_dependencies)

        pypi_table = Table(title="PyPI check")
        pypi_table.add_column("Package", style="cyan")
        pypi_table.add_column("Status", style="green")
        pypi_table.add_column("Latest version", style="yellow")

        for package in pypi_results:
            status = "found" if package.exists else "not found"
            latest_version = package.latest_version or "-"

            pypi_table.add_row(package.name, status, latest_version)

        console.print(pypi_table)

    if analysis.pyproject_info is not None:
        pyproject_info = analysis.pyproject_info

        pyproject_table = Table(title="PyProject info")
        pyproject_table.add_column("Field", style="cyan")
        pyproject_table.add_column("Value", style="green")

        pyproject_table.add_row("Project name", pyproject_info.project_name or "-")
        pyproject_table.add_row(
            "Dependencies",
            "\n".join(pyproject_info.dependencies) or "-",
        )
        pyproject_table.add_row(
            "Build system requires",
            "\n".join(pyproject_info.build_system_requires) or "-",
        )

        if pyproject_info.optional_dependencies:
            optional_text = "\n".join(
                f"{group}: {', '.join(deps)}"
                for group, deps in pyproject_info.optional_dependencies.items()
            )
        else:
            optional_text = "-"

        pyproject_table.add_row("Optional dependencies", optional_text)

        console.print(pyproject_table)

    if analysis.conda_environment is not None:
        conda_env = analysis.conda_environment

        conda_table = Table(title="Conda environment")
        conda_table.add_column("Field", style="cyan")
        conda_table.add_column("Value", style="green")

        conda_table.add_row("Name", conda_env.name or "-")
        conda_table.add_row(
            "Conda packages",
            "\n".join(conda_env.conda_dependencies) or "-",
        )
        conda_table.add_row(
            "Pip packages",
            "\n".join(conda_env.pip_dependencies) or "-",
        )

        console.print(conda_table)

    if analysis.dockerfile_info is not None:
        docker_info = analysis.dockerfile_info

        docker_table = Table(title="Dockerfile info")
        docker_table.add_column("Field", style="cyan")
        docker_table.add_column("Value", style="green")

        docker_table.add_row(
            "Base image",
            "\n".join(docker_info.base_images) or "-",
        )
        docker_table.add_row(
            "Apt packages",
            "\n".join(docker_info.apt_packages) or "-",
        )
        docker_table.add_row(
            "Pip packages",
            "\n".join(docker_info.pip_packages) or "-",
        )

        console.print(docker_table)

    if analysis.ros_package_info is not None:
        ros_info = analysis.ros_package_info

        ros_table = Table(title="ROS package info")
        ros_table.add_column("Field", style="cyan")
        ros_table.add_column("Value", style="green")

        ros_table.add_row("Package name", ros_info.name or "-")
        ros_table.add_row(
            "Build tool dependencies",
            "\n".join(ros_info.build_tool_dependencies) or "-",
        )
        ros_table.add_row(
            "Build dependencies",
            "\n".join(ros_info.build_dependencies) or "-",
        )
        ros_table.add_row(
            "Execution dependencies",
            "\n".join(ros_info.execution_dependencies) or "-",
        )
        ros_table.add_row(
            "Test dependencies",
            "\n".join(ros_info.test_dependencies) or "-",
        )

        console.print(ros_table)

    if analysis.cmake_info is not None:
        cmake_info = analysis.cmake_info

        cmake_table = Table(title="CMake info")
        cmake_table.add_column("Field", style="cyan")
        cmake_table.add_column("Value", style="green")

        cmake_table.add_row("Project name", cmake_info.project_name or "-")
        cmake_table.add_row("Minimum version", cmake_info.minimum_version or "-")
        cmake_table.add_row(
            "Found packages",
            "\n".join(cmake_info.found_packages) or "-",
        )

        console.print(cmake_table)

    install_plan = create_install_plan(analysis)

    plan_table = Table(title="Install plan")
    plan_table.add_column("Field", style="cyan")
    plan_table.add_column("Value", style="green")

    plan_table.add_row("Recommended mode", install_plan.recommended_mode)
    plan_table.add_row("Reason", install_plan.reason)
    plan_table.add_row("Steps", "\n".join(install_plan.steps))

    console.print(plan_table)

    if "docker" in analysis.detected_ecosystems:
        console.print(
            "[yellow]Recommendation:[/yellow] Docker installation may be available."
        )
    elif "ros" in analysis.detected_ecosystems:
        console.print(
            "[yellow]Recommendation:[/yellow] "
            "Use rosdep or Docker for ROS dependencies."
        )
    elif "python" in analysis.detected_ecosystems:
        console.print(
            "[yellow]Recommendation:[/yellow] "
            "Python environment installation is possible."
        )
    else:
        console.print("[yellow]Recommendation:[/yellow] Manual inspection is needed.")

    warnings = generate_compatibility_warnings(analysis, system_info)

    if warnings:
        warning_table = Table(title="Compatibility warnings")
        warning_table.add_column("Warning", style="yellow")

        for warning in warnings:
            warning_table.add_row(warning)

        console.print(warning_table)

    if report:
        report_text = generate_markdown_report(
            analysis=analysis,
            install_plan=install_plan,
            system_info=system_info,
        )
        report_path = write_markdown_report(report_text)
        console.print(f"[bold green]Report written to:[/bold green] {report_path}")


@app.command()
def system() -> None:
    """Show basic system diagnostics."""
    info = get_system_info()

    table = Table(title="System check")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("OS", info.os_name)
    table.add_row("OS version", info.os_version)
    table.add_row("Architecture", info.architecture)
    table.add_row("Python", info.python_version)
    table.add_row("Git", "found" if info.git_available else "not found")
    table.add_row("Docker", "found" if info.docker_available else "not found")
    table.add_row(
        "NVIDIA GPU",
        "detected" if info.nvidia_gpu_available else "not detected",
    )

    console.print(table)


@app.command()
def version() -> None:
    """Show SimFix version."""
    console.print(f"simfix {__version__}")
