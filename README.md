# SimFix

SimFix is a command-line tool for diagnosing and fixing common setup problems in simulator repositories.

It inspects a project, detects dependency files, checks Python packages, reports system requirements, and suggests a safe installation plan.

## Installation

Install SimFix from PyPI:

```bash
pip install simfix
```

Check that it installed correctly:

```bash
simfix --version
```

You can also check your system:

```bash
simfix system
```

## Quick start

Analyze a simulator repository:

```bash
simfix doctor <repo>
```

Example:

```bash
simfix doctor ../my_simulator_repo
```

Apply supported automatic fixes:

```bash
simfix fix <repo>
```

Generate an installation plan:

```bash
simfix plan <repo>
```

Show suggested installation commands:

```bash
simfix commands <repo>
```

Generate a Markdown report:

```bash
simfix doctor <repo> --report
```

Analyze a GitHub repository directly:

```bash
simfix doctor https://github.com/user/repository.git
```

## Environment recommendations

Some simulator projects require system-level or vendor-managed dependencies such as NVIDIA drivers, CUDA, ROS, Gazebo, Isaac Gym, or Isaac Sim. SimFix does not install these automatically because they depend on the operating system, hardware, driver compatibility, administrator permissions, and vendor installation steps.

Use:

```bash
simfix recommendations <repo>
```
## Main commands

```bash
simfix --version
simfix system
simfix doctor <repo>
simfix doctor <repo> --report
simfix recommendations <repo>
simfix fix <repo>
simfix analyze <repo>
simfix plan <repo>
simfix commands <repo>
```

## What SimFix can detect

SimFix currently detects:

* `requirements.txt`
* `setup.py`
* `pyproject.toml`
* `environment.yml` / `environment.yaml`
* `Dockerfile`
* `package.xml`
* `CMakeLists.txt`

## What SimFix can fix

The `simfix fix` command currently supports:

* Resolving `requirements.txt` using `uv`
* Normalizing invalid pip syntax such as `package=version` to `package==version`
* Repairing clear dependency conflicts by removing direct conflicting pins and letting the resolver choose compatible versions
* Cleaning duplicate dependencies in `environment.yml`
* Creating CUDA/GPU Dockerfiles for GPU-based simulator projects
* Creating ROS Dockerfiles from `package.xml`
* Creating Docker run helper scripts
* Initializing Git submodules
* Pulling Git LFS assets when Git LFS is available

SimFix always modifies files in place, so review changes with:

```bash
git diff
```

## Example

```bash
simfix doctor ../my_simulator_repo
```

Example output:

```text
SimFix Doctor
Repository: /path/to/my_simulator_repo

Detected dependency files
requirements.txt: yes
setup.py: yes
Dockerfile: no

Detected ecosystem(s): python

PyPI check
numpy: found
matplotlib: found
isaacgym: not found

Recommendation:
Some dependencies are not available on PyPI.
Manual/vendor installation may be required.
```

## Important notes

SimFix does not install GPU drivers, CUDA drivers, ROS, Isaac Gym, Isaac Sim, or other vendor software automatically.

For GPU simulator projects, SimFix may create a CUDA Dockerfile, but your machine still needs a working NVIDIA driver and NVIDIA Container Toolkit to run GPU containers.

Some packages, such as NVIDIA Isaac Gym, are not available on PyPI and must be installed manually.

## Development installation

For contributors, clone the repository:

```bash
git clone https://github.com/hrehmaan/simfix.git
cd simfix
```

Install in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Install pre-commit hooks:

```bash
pre-commit install
```

Run tests:

```bash
pytest
```

Run all checks:

```bash
pre-commit run --all-files
```

## Project status

SimFix is in early development.

The goal is to make simulator setup easier by combining repository analysis, system diagnostics, dependency checks, resolver-based repair, Docker guidance, and clear warnings for manual/vendor dependencies.

## Contributing

Contributions are welcome.

Before opening a pull request, please first create an issue describing the bug, feature request, or improvement you want to work on. This helps avoid duplicate work and makes it easier to discuss the best solution before implementation.

Recommended contribution workflow:

```bash
# 1. Create an issue on GitHub first
# 2. Fork the repository
# 3. Create a new branch
git checkout -b fix-or-feature-name

# 4. Make your changes
# 5. Run checks
pytest
pre-commit run --all-files

# 6. Open a pull request and link it to the issue
