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
from simfix.system import get_system_info

app = typer.Typer(
    name="simfix",
    help="Smart dependency checker and installer assistant for simulator repositories.",
)

console = Console()


@app.command()
def doctor(repo: str) -> None:
    """Analyze a local path or Git repository URL."""
    if is_git_url(repo):
        console.print("[bold blue]Cloning repository...[/bold blue]")
        repo_path = clone_repo(repo)
    else:
        repo_path = Path(repo)

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

    if analysis.python_requirements:
        deps_table = Table(title="Python packages")
        deps_table.add_column("Dependency", style="cyan")

        for dependency in analysis.python_requirements:
            deps_table.add_row(dependency)

        console.print(deps_table)

        pypi_results = check_pypi_packages(analysis.python_requirements)

        pypi_table = Table(title="PyPI check")
        pypi_table.add_column("Package", style="cyan")
        pypi_table.add_column("Status", style="green")
        pypi_table.add_column("Latest version", style="yellow")

        for package in pypi_results:
            status = "found" if package.exists else "not found"
            latest_version = package.latest_version or "-"

            pypi_table.add_row(package.name, status, latest_version)

        console.print(pypi_table)

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
