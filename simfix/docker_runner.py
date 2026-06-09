from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simfix.cuda_docker import detect_gpu_project


@dataclass(frozen=True)
class DockerRunFixResult:
    """Result of creating a Docker run helper script."""

    file_path: Path
    changed: bool
    message: str


def _docker_run_script(image_name: str, use_gpu: bool) -> str:
    """Return a Docker build/run helper script."""
    gpu_flag = " --gpus all" if use_gpu else ""

    return f"""#!/usr/bin/env bash
set -e

IMAGE_NAME="{image_name}"

docker build -t "$IMAGE_NAME" .

docker run --rm -it{gpu_flag} \\
    -v "$PWD:/workspace" \\
    -w /workspace \\
    "$IMAGE_NAME"
"""


def create_docker_run_helper(repo_path: str | Path) -> DockerRunFixResult | None:
    """Create a Docker build/run helper script when Dockerfile exists."""
    path = Path(repo_path).expanduser().resolve()
    dockerfile_path = path / "Dockerfile"

    if not dockerfile_path.exists():
        return None

    script_path = path / "run_simfix_docker.sh"

    if script_path.exists():
        return DockerRunFixResult(
            file_path=script_path,
            changed=False,
            message="Docker run helper already exists. SimFix did not overwrite it.",
        )

    image_name = f"simfix-{path.name}".lower().replace("_", "-")
    use_gpu = detect_gpu_project(path)

    script_path.write_text(
        _docker_run_script(image_name=image_name, use_gpu=use_gpu),
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    if use_gpu:
        message = "Created Docker run helper with GPU support."
    else:
        message = "Created Docker run helper."

    return DockerRunFixResult(
        file_path=script_path,
        changed=True,
        message=message,
    )
