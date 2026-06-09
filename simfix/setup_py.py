from __future__ import annotations

import ast
from pathlib import Path


def parse_setup_py_dependencies(setup_py_path: str | Path) -> list[str]:
    """Parse simple install_requires dependencies from setup.py."""
    path = Path(setup_py_path).expanduser().resolve()

    if not path.exists():
        return []

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    dependencies: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        for keyword in node.keywords:
            if keyword.arg != "install_requires":
                continue

            dependencies.extend(_parse_dependency_list(keyword.value))

    return dependencies


def _parse_dependency_list(node: ast.AST) -> list[str]:
    """Parse dependency list values from an AST node."""
    if not isinstance(node, ast.List | ast.Tuple):
        return []

    dependencies: list[str] = []

    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            dependencies.append(element.value)

    return dependencies
