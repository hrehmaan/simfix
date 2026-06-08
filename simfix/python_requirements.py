from __future__ import annotations

from pathlib import Path


def parse_requirements_file(path: str | Path) -> list[str]:
    """Parse a requirements.txt file and return dependency lines.

    This parser keeps version specifiers but ignores comments, empty lines,
    editable installs, recursive requirement files, and pip options.
    """
    requirements_path = Path(path).expanduser().resolve()

    if not requirements_path.exists():
        return []

    dependencies: list[str] = []

    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        if clean_line.startswith("#"):
            continue

        if clean_line.startswith(("-r", "--requirement")):
            continue

        if clean_line.startswith(("-e", "--editable")):
            continue

        if clean_line.startswith(("-", "--")):
            continue

        if " #" in clean_line:
            clean_line = clean_line.split(" #", maxsplit=1)[0].strip()

        dependencies.append(clean_line)

    return dependencies
