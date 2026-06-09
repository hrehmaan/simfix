#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 0.1.2"
    exit 1
fi

VERSION="$1"

echo "Preparing SimFix release $VERSION"

python - <<PY
from pathlib import Path

version = "$VERSION"

pyproject = Path("pyproject.toml")
text = pyproject.read_text(encoding="utf-8")
text = text.replace(
    next(line for line in text.splitlines() if line.startswith("version = ")),
    f'version = "{version}"',
)
pyproject.write_text(text, encoding="utf-8")

init_file = Path("simfix/__init__.py")
text = init_file.read_text(encoding="utf-8")
lines = []
for line in text.splitlines():
    if line.startswith("__version__ = "):
        lines.append(f'__version__ = "{version}"')
    else:
        lines.append(line)
init_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

test_file = Path("tests/test_basic.py")
text = test_file.read_text(encoding="utf-8")
lines = []
for line in text.splitlines():
    if "assert __version__ ==" in line:
        indent = line[: len(line) - len(line.lstrip())]
        lines.append(f'{indent}assert __version__ == "{version}"')
    else:
        lines.append(line)
test_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

echo "Running tests"
pytest

echo "Running pre-commit"
pre-commit run --all-files

echo "Cleaning old builds"
rm -rf dist build *.egg-info

echo "Building package"
python -m build

echo "Checking package"
python -m twine check dist/*

echo "Uploading to PyPI"
python -m twine upload dist/*

echo "Release $VERSION uploaded to PyPI"
echo "Now commit and tag:"
echo "  git add ."
echo "  git commit -m \"Release version $VERSION\""
echo "  git tag v$VERSION"
echo "  git push origin main"
echo "  git push origin v$VERSION"
