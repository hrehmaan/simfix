from __future__ import annotations

import typer
from rich.console import Console

from simfix import __version__

app = typer.Typer(
    name="simfix",
    help="Smart dependency checker and installer assistant for simulator repositories.",
)

console = Console()


@app.command()
def doctor(repo_url: str) -> None:
    """Analyze a simulator repository and report possible dependency issues."""
    console.print("[bold green]SimFix Doctor[/bold green]")
    console.print(f"Repository: {repo_url}")
    console.print("Status: project structure is ready.")


@app.command()
def version() -> None:
    """Show SimFix version."""
    console.print(f"simfix {__version__}")
