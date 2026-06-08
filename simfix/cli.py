from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from simfix import __version__
from simfix.analyzer import analyze_repo

app = typer.Typer(
    name="simfix",
    help="Smart dependency checker and installer assistant for simulator repositories.",
)

console = Console()


@app.command()
def doctor(repo_path: str) -> None:
    """Analyze a local simulator repository and report possible dependency issues."""
    analysis = analyze_repo(Path(repo_path))

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
