from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from simfix import __version__
from simfix.analyzer import analyze_repo
from simfix.pypi import check_pypi_packages
from simfix.repo import clone_repo, is_git_url

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


@app.command()
def version() -> None:
    """Show SimFix version."""
    console.print(f"simfix {__version__}")
