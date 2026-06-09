# SimFix

SimFix is a dependency checker and installation assistant for simulator repositories.

It helps users diagnose common installation problems by inspecting repository files, detecting dependency systems, checking Python packages, identifying system requirements, and suggesting a safe installation plan.

SimFix is designed for simulator projects where installation can fail because of missing dependencies, version conflicts, GPU/CUDA requirements, ROS dependencies, Docker setup issues, or unclear setup instructions.

## Features

SimFix can analyze both local repositories and remote GitHub/GitLab repositories.

It currently supports:

* Local repository analysis
* GitHub/GitLab repository analysis by cloning into a local workspace
* Dependency file detection
* Python dependency parsing
* PyPI package checks
* Basic installation planning
* System diagnostics
* Safe dependency fixes for selected file types
* Docker helper generation for supported simulator projects

## Supported dependency files

SimFix can detect and inspect:

* `requirements.txt`
* `setup.py`
* `pyproject.toml`
* `environment.yml` / `environment.yaml`
* `Dockerfile`
* `package.xml`
* `CMakeLists.txt`

## System diagnostics

SimFix can report:

* Operating system
* CPU architecture
* Python version
* Git availability
* Docker availability
* Conda/mamba availability
* NVIDIA GPU availability
* NVIDIA driver information
* CUDA toolkit availability

## Automatic fixes

The `simfix fix` command currently supports:

* Resolving `requirements.txt` with `uv`
* Normalizing invalid pip syntax such as `package=version` to `package==version`
* Repairing clear resolver conflicts by removing direct conflicting pins and letting `uv` choose compatible versions
* Cleaning duplicate dependencies in `environment.yml`
* Creating CUDA/GPU Dockerfiles for GPU-based simulator projects
* Creating ROS Dockerfiles from `package.xml`
* Creating general system dependency Dockerfiles for CMake/C++ simulator projects
* Initializing Git submodules
* Pulling Git LFS assets when Git LFS is available
* Creating a Docker run helper script

For GPU projects, SimFix can create a CUDA-based Dockerfile. The host machine still needs a working NVIDIA driver and NVIDIA Container Toolkit to run GPU containers.

SimFix does not automatically install vendor software such as NVIDIA Isaac Gym, Isaac Sim, CUDA drivers, or system-level GPU drivers. These dependencies must be installed manually.

## Installation for development

Clone the repository:

```bash
git clone https://github.com/hrehmaan/simfix.git
cd simfix
```

Install in editable mode with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Install pre-commit hooks:

```bash
pre-commit install
```

## Usage

Check your system:

```bash
simfix system
```

Analyze a repository:

```bash
simfix doctor <repo>
```

Example:

```bash
simfix doctor ../simfix_test
```

Analyze a repository and show detected metadata:

```bash
simfix analyze <repo>
```

Generate an installation plan:

```bash
simfix plan <repo>
```

Generate a Markdown report:

```bash
simfix doctor <repo> --report
```

Show suggested installation commands without running them:

```bash
simfix commands <repo>
```

Apply supported automatic fixes:

```bash
simfix fix <repo>
```

Analyze a remote GitHub repository:

```bash
simfix doctor https://github.com/hrehmaan/simfix.git
```

Show the installed SimFix version:

```bash
simfix version
```

## Main commands

```text
simfix system
simfix doctor <repo>
simfix doctor <repo> --report
simfix analyze <repo>
simfix plan <repo>
simfix commands <repo>
simfix fix <repo>
simfix version
```

## Example output

```text
SimFix Doctor
Repository: /path/to/repository

Detected dependency files
requirements.txt: yes
setup.py: yes
pyproject.toml: no
environment.yml: no
Dockerfile: no
package.xml / ROS: no
CMakeLists.txt: no

Detected ecosystem(s): python

Python packages
- numpy
- matplotlib

PyPI check
- numpy: found
- matplotlib: found

Install plan
Recommended mode: python
Reason: Python dependency files were found.

Recommendation:
Python environment installation is possible.
```

## Example: fixing a Python dependency conflict

If a repository contains conflicting Python requirements such as:

```text
urdfpy==0.0.22
networkx==3.1
```

and the resolver reports that `urdfpy==0.0.22` requires `networkx==2.2`, SimFix does not blindly choose a version itself.

Instead, SimFix removes the direct conflicting pin and lets `uv` resolve the compatible version.

This keeps the resolver as the authority and avoids hard-coding risky downgrades.

## Example: vendor dependency detection

Some simulator dependencies are not available on PyPI. For example, NVIDIA Isaac Gym is a vendor dependency and cannot be installed with:

```bash
python -m pip install isaacgym
```

In such cases, SimFix reports the missing package and indicates that manual installation is required.

For these projects, the correct setup may require:

* Linux
* NVIDIA GPU
* NVIDIA driver
* CUDA support
* Vendor SDK installation

## Development checks

Run tests:

```bash
pytest
```

Run pre-commit:

```bash
pre-commit run --all-files
```

## Project status

SimFix is in early development.

The current focus is safe repository analysis, dependency diagnosis, installation planning, and targeted automatic fixes for common simulator setup problems.

The long-term goal is to make simulator setup easier by combining repository analysis, system diagnostics, dependency checks, resolver-based repair, Docker guidance, and clear manual-install warnings for vendor dependencies.
