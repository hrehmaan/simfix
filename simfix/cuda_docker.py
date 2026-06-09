from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simfix.system import get_system_info

GPU_KEYWORDS = {
    "cuda",
    "cudnn",
    "cupy",
    "nvidia",
    "nvcc",
    "torch",
    "tensorflow",
    "numba.cuda",
    "jax[cuda",
    "onnxruntime-gpu",
}


@dataclass(frozen=True)
class CudaDockerFixResult:
    """Result of creating a CUDA Dockerfile."""

    file_path: Path
    changed: bool
    message: str


def _read_text_if_exists(path: Path) -> str:
    """Read text from a file if it exists."""
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8", errors="ignore")


def _repo_has_cuda_files(repo_path: Path) -> bool:
    """Return True if repository contains CUDA source files."""
    cuda_suffixes = {".cu", ".cuh"}

    for file_path in repo_path.rglob("*"):
        if ".git" in file_path.parts:
            continue

        if file_path.is_file() and file_path.suffix.lower() in cuda_suffixes:
            return True

    return False


def detect_gpu_project(repo_path: str | Path) -> bool:
    """Detect whether a repository likely needs GPU/CUDA support."""
    path = Path(repo_path).expanduser().resolve()

    searchable_text = "\n".join(
        [
            _read_text_if_exists(path / "requirements.txt"),
            _read_text_if_exists(path / "pyproject.toml"),
            _read_text_if_exists(path / "environment.yml"),
            _read_text_if_exists(path / "environment.yaml"),
            _read_text_if_exists(path / "README.md"),
            _read_text_if_exists(path / "readme.md"),
            _read_text_if_exists(path / "CMakeLists.txt"),
        ]
    ).lower()

    if any(keyword in searchable_text for keyword in GPU_KEYWORDS):
        return True

    return _repo_has_cuda_files(path)


def _gpu_status_message() -> str:
    """Return host GPU/driver status message."""
    system_info = get_system_info()

    if system_info.nvidia_gpu_available:
        return (
            " NVIDIA GPU detected"
            f" with driver {system_info.nvidia_driver_version or 'unknown'}"
            f" and CUDA {system_info.nvidia_cuda_version or 'unknown'}."
        )

    return (
        " No NVIDIA GPU/driver was detected on this machine. "
        "GPU containers will need a working NVIDIA driver and "
        "NVIDIA Container Toolkit on the host."
    )


def _cuda_dockerfile(has_requirements: bool) -> str:
    """Return a CUDA Dockerfile."""
    install_requirements = ""

    if has_requirements:
        install_requirements = """

COPY requirements.txt /workspace/requirements.txt
RUN python3 -m pip install --upgrade pip && \\
    python3 -m pip install -r /workspace/requirements.txt
"""

    return f"""FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \\
    build-essential \\
    cmake \\
    git \\
    python3 \\
    python3-pip \\
    python3-venv \\
    libgl1 \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
{install_requirements}
COPY . /workspace

CMD ["/bin/bash"]
"""


def create_cuda_dockerfile(repo_path: str | Path) -> CudaDockerFixResult | None:
    """Create a CUDA Dockerfile for GPU projects.

    This creates Dockerfile only when GPU/CUDA clues exist and Dockerfile is missing.
    """
    path = Path(repo_path).expanduser().resolve()

    if not detect_gpu_project(path):
        return None

    dockerfile_path = path / "Dockerfile"

    if dockerfile_path.exists():
        return CudaDockerFixResult(
            file_path=dockerfile_path,
            changed=False,
            message=(
                "Dockerfile already exists. SimFix did not overwrite it."
                + _gpu_status_message()
            ),
        )

    has_requirements = (path / "requirements.txt").exists()

    dockerfile_path.write_text(
        _cuda_dockerfile(has_requirements=has_requirements),
        encoding="utf-8",
    )

    return CudaDockerFixResult(
        file_path=dockerfile_path,
        changed=True,
        message="Created CUDA Dockerfile for GPU project." + _gpu_status_message(),
    )
