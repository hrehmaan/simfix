#!/bin/bash
set -e

pytest
pre-commit run --all-files

rm -rf dist build *.egg-info
python -m build
python -m twine check dist/*
python -m twine upload dist/*
