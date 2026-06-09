from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

COMMON_SIMULATOR_APT_PACKAGES = [
    "build-essential",
    "cmake",
    "git",
    "pkg-config",
    "python3",
    "python3-pip",
    "libgl1",
    "libglib2.0-0",
    "libx11-6",
    "libxext6",
    "libxrender1",
    "libsm6",
    "libice6",
    "libeigen3-dev",
    "libboost-all-dev",
]


SYSTEM_KEYWORDS = {
    "cmake",
    "find_package",
    "opengl",
    "glfw",
    "glew",
    "eigen",
    "boost",
    "sdl",
    "opencv",
    "libgl",
    "build-essential",
}


@dataclass(frozen=True)
class SystemDockerFixResult:
    """Result of creating or updating a system dependency Dockerfile."""

    file_path: Path
    changed: bool
    message: str


def _read_text_if_exists(path: Path) -> str:
    """Read text from a file if it exists."""
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8", errors="ignore")


def detect_system_dependency_project(repo_path: str | Path) -> bool:
    """Detect whether a repository likely needs Linux system packages."""
    path = Path(repo_path).expanduser().resolve()

    searchable_text = "\n".join(
        [
            _read_text_if_exists(path / "CMakeLists.txt"),
            _read_text_if_exists(path / "README.md"),
            _read_text_if_exists(path / "readme.md"),
            _read_text_if_exists(path / "Dockerfile"),
            _read_text_if_exists(path / "setup.py"),
            _read_text_if_exists(path / "pyproject.toml"),
        ]
    ).lower()

    if any(keyword in searchable_text for keyword in SYSTEM_KEYWORDS):
        return True

    cpp_suffixes = {".cpp", ".cc", ".cxx", ".c", ".hpp", ".h"}

    for file_path in path.rglob("*"):
        if ".git" in file_path.parts:
            continue

        if file_path.is_file() and file_path.suffix.lower() in cpp_suffixes:
            return True

    return False


def _ubuntu_dockerfile() -> str:
    """Return a Dockerfile with common simulator system packages."""
    packages = " \\\n    ".join(COMMON_SIMULATOR_APT_PACKAGES)

    return f"""FROM ubuntu:22.04

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \\
    {packages} \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . /workspace

CMD ["/bin/bash"]
"""


def _extract_existing_apt_packages(dockerfile_text: str) -> set[str]:
    """Extract simple package names already present in a Dockerfile."""
    existing_packages: set[str] = set()

    for package in COMMON_SIMULATOR_APT_PACKAGES:
        if package in dockerfile_text:
            existing_packages.add(package)

    return existing_packages


def _append_apt_install_block(dockerfile_text: str, packages: list[str]) -> str:
    """Append an apt-get install block to an existing Dockerfile."""
    package_lines = " \\\n    ".join(packages)

    block = f"""

# Added by SimFix: common simulator system dependencies
RUN apt-get update && apt-get install -y \\
    {package_lines} \\
    && rm -rf /var/lib/apt/lists/*
"""

    return dockerfile_text.rstrip() + block + "\n"


def fix_system_dockerfile(repo_path: str | Path) -> SystemDockerFixResult | None:
    """Create or update Dockerfile with common simulator system packages."""
    path = Path(repo_path).expanduser().resolve()

    if not detect_system_dependency_project(path):
        return None

    dockerfile_path = path / "Dockerfile"

    if not dockerfile_path.exists():
        dockerfile_path.write_text(_ubuntu_dockerfile(), encoding="utf-8")

        return SystemDockerFixResult(
            file_path=dockerfile_path,
            changed=True,
            message="Created Dockerfile with common simulator system packages.",
        )

    old_text = dockerfile_path.read_text(encoding="utf-8")
    existing_packages = _extract_existing_apt_packages(old_text)
    missing_packages = [
        package
        for package in COMMON_SIMULATOR_APT_PACKAGES
        if package not in existing_packages
    ]

    if not missing_packages:
        return SystemDockerFixResult(
            file_path=dockerfile_path,
            changed=False,
            message="Dockerfile already contains common simulator system packages.",
        )

    new_text = _append_apt_install_block(old_text, missing_packages)
    dockerfile_path.write_text(new_text, encoding="utf-8")

    return SystemDockerFixResult(
        file_path=dockerfile_path,
        changed=True,
        message="Updated Dockerfile with missing simulator system packages.",
    )
