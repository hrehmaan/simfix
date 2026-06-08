from __future__ import annotations

import re
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class PyPIPackageInfo:
    """Basic package information from PyPI."""

    name: str
    exists: bool
    latest_version: str | None = None
    error: str | None = None


def normalize_requirement_name(requirement: str) -> str:
    """Extract package name from a requirement string.

    Examples:
        numpy>=1.26 -> numpy
        matplotlib==3.8.0 -> matplotlib
        scipy[dev]>=1.11 -> scipy
    """
    requirement = requirement.strip()

    match = re.match(r"^[A-Za-z0-9_.-]+", requirement)

    if match is None:
        return requirement

    name = match.group(0)

    if "[" in name:
        name = name.split("[", maxsplit=1)[0]

    return name


def check_pypi_package(package_name: str, timeout: float = 5.0) -> PyPIPackageInfo:
    """Check whether a package exists on PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"

    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return PyPIPackageInfo(
            name=package_name,
            exists=False,
            error=str(exc),
        )

    if response.status_code == 404:
        return PyPIPackageInfo(name=package_name, exists=False)

    if response.status_code != 200:
        return PyPIPackageInfo(
            name=package_name,
            exists=False,
            error=f"HTTP {response.status_code}",
        )

    data = response.json()
    latest_version = data.get("info", {}).get("version")

    return PyPIPackageInfo(
        name=package_name,
        exists=True,
        latest_version=latest_version,
    )


def check_pypi_packages(requirements: list[str]) -> list[PyPIPackageInfo]:
    """Check multiple requirement strings against PyPI."""
    results: list[PyPIPackageInfo] = []

    for requirement in requirements:
        package_name = normalize_requirement_name(requirement)
        results.append(check_pypi_package(package_name))

    return results
