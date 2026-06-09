from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DockerfileInfo:
    """Basic information extracted from a Dockerfile."""

    base_images: list[str]
    apt_packages: list[str]
    pip_packages: list[str]


def _join_continued_lines(text: str) -> list[str]:
    """Join Dockerfile lines ending with backslash."""
    joined_lines: list[str] = []
    current = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.endswith("\\"):
            current += line[:-1].strip() + " "
        else:
            current += line
            joined_lines.append(current.strip())
            current = ""

    if current:
        joined_lines.append(current.strip())

    return joined_lines


def _clean_package_token(token: str) -> str:
    """Clean common shell tokens from a package name."""
    return token.strip().strip("\\").strip()


def parse_dockerfile(path: str | Path) -> DockerfileInfo | None:
    """Parse a Dockerfile and extract basic dependency hints."""
    dockerfile_path = Path(path).expanduser().resolve()

    if not dockerfile_path.exists():
        return None

    lines = _join_continued_lines(dockerfile_path.read_text(encoding="utf-8"))

    base_images: list[str] = []
    apt_packages: list[str] = []
    pip_packages: list[str] = []

    for line in lines:
        upper_line = line.upper()

        if upper_line.startswith("FROM "):
            parts = line.split()
            if len(parts) >= 2:
                base_images.append(parts[1])

        if "apt-get install" in line or "apt install" in line:
            install_part = re.split(r"apt-get install|apt install", line, maxsplit=1)[
                -1
            ]
            tokens = install_part.split()

            for token in tokens:
                package = _clean_package_token(token)

                if not package:
                    continue

                if package.startswith("-"):
                    continue

                if package in {"&&", ";", "apt-get", "apt", "install"}:
                    continue

                if package.startswith(("rm", "/var/lib/apt/lists")):
                    continue

                apt_packages.append(package)

        if "pip install" in line or "python -m pip install" in line:
            install_part = re.split(
                r"python -m pip install|pip install",
                line,
                maxsplit=1,
            )[-1]
            tokens = install_part.split()

            for token in tokens:
                package = _clean_package_token(token)

                if not package:
                    continue

                if package.startswith("-"):
                    continue

                if package in {"&&", ";"}:
                    continue

                pip_packages.append(package)

    return DockerfileInfo(
        base_images=base_images,
        apt_packages=apt_packages,
        pip_packages=pip_packages,
    )
