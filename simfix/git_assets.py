from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitAssetsFixResult:
    """Result of fixing git-managed assets."""

    changed: bool
    message: str


def _command_exists(command: str) -> bool:
    """Return True if a command exists on PATH."""
    return shutil.which(command) is not None


def _run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a command in a repository."""
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _is_git_repo(path: Path) -> bool:
    """Return True if path is inside a Git repository."""
    result = _run_command(["git", "rev-parse", "--is-inside-work-tree"], path)

    return result.returncode == 0 and result.stdout.strip() == "true"


def _uses_git_lfs(path: Path) -> bool:
    """Return True if repository appears to use Git LFS."""
    attributes_path = path / ".gitattributes"

    if not attributes_path.exists():
        return False

    attributes_text = attributes_path.read_text(encoding="utf-8", errors="ignore")

    return "filter=lfs" in attributes_text


def fix_git_assets(repo_path: str | Path) -> GitAssetsFixResult | None:
    """Fix missing git submodules and Git LFS assets."""
    path = Path(repo_path).expanduser().resolve()

    if not _command_exists("git"):
        return GitAssetsFixResult(
            changed=False,
            message="git was not found, so SimFix could not fix git assets.",
        )

    if not _is_git_repo(path):
        return None

    messages: list[str] = []
    changed = False

    gitmodules_path = path / ".gitmodules"

    if gitmodules_path.exists():
        result = _run_command(
            ["git", "submodule", "update", "--init", "--recursive"],
            path,
        )

        if result.returncode == 0:
            messages.append("Git submodules updated successfully.")
            changed = True
        else:
            messages.append(
                "Git submodule update failed: "
                + (result.stderr.strip() or result.stdout.strip())
            )

    if _uses_git_lfs(path):
        if not _command_exists("git-lfs") and not _command_exists("git-lfs.exe"):
            messages.append(
                "Git LFS files detected, but git-lfs was not found. "
                "Install Git LFS and run: git lfs pull"
            )
        else:
            result = _run_command(["git", "lfs", "pull"], path)

            if result.returncode == 0:
                messages.append("Git LFS assets pulled successfully.")
                changed = True
            else:
                messages.append(
                    "Git LFS pull failed: "
                    + (result.stderr.strip() or result.stdout.strip())
                )

    if not messages:
        return None

    return GitAssetsFixResult(
        changed=changed,
        message=" ".join(messages),
    )
