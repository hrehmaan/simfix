from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def is_git_url(value: str) -> bool:
    """Return True if the value looks like a GitHub/GitLab repository URL."""
    parsed = urlparse(value)

    return parsed.scheme in {"http", "https", "git"} and parsed.netloc != ""


def repo_name_from_url(repo_url: str) -> str:
    """Extract a clean repository name from a Git URL."""
    path = urlparse(repo_url).path.rstrip("/")
    name = Path(path).name

    if name.endswith(".git"):
        name = name.removesuffix(".git")

    if not name:
        raise ValueError(f"Could not determine repository name from URL: {repo_url}")

    return name


def clone_repo(repo_url: str, workspace: str | Path = "workspace") -> Path:
    """Clone a repository into the workspace folder and return its local path."""
    workspace_path = Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    repo_name = repo_name_from_url(repo_url)
    destination = workspace_path / repo_name

    if destination.exists():
        shutil.rmtree(destination)

    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(destination)],
        check=True,
    )

    return destination
