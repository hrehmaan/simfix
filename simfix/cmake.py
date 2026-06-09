from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CMakeInfo:
    """Basic information extracted from CMakeLists.txt."""

    minimum_version: str | None
    project_name: str | None
    found_packages: list[str]


def _remove_comments(text: str) -> str:
    """Remove simple CMake line comments."""
    lines: list[str] = []

    for line in text.splitlines():
        clean_line = line.split("#", maxsplit=1)[0]
        lines.append(clean_line)

    return "\n".join(lines)


def parse_cmake_file(path: str | Path) -> CMakeInfo | None:
    """Parse a CMakeLists.txt file and extract basic information."""
    cmake_path = Path(path).expanduser().resolve()

    if not cmake_path.exists():
        return None

    text = _remove_comments(cmake_path.read_text(encoding="utf-8"))

    minimum_version_match = re.search(
        r"cmake_minimum_required\s*\(\s*VERSION\s+([^) \n]+)",
        text,
        flags=re.IGNORECASE,
    )

    project_match = re.search(
        r"project\s*\(\s*([A-Za-z0-9_.-]+)",
        text,
        flags=re.IGNORECASE,
    )

    found_packages = re.findall(
        r"find_package\s*\(\s*([A-Za-z0-9_.-]+)",
        text,
        flags=re.IGNORECASE,
    )

    return CMakeInfo(
        minimum_version=(
            minimum_version_match.group(1) if minimum_version_match else None
        ),
        project_name=project_match.group(1) if project_match else None,
        found_packages=list(dict.fromkeys(found_packages)),
    )
