# SimFix

SimFix is a smart dependency checker and installer assistant for simulator repositories.

The goal of SimFix is to help users diagnose common installation problems in simulator projects by inspecting repository files, detecting dependency systems, checking Python packages, and generating a basic installation plan.

SimFix is designed for projects where installation often fails because of missing dependencies, version conflicts, system mismatches, or unclear setup instructions.

## Current features

* Analyze a local repository path
* Analyze a GitHub/GitLab repository URL by cloning it into a local workspace
* Detect common dependency files:

  * `requirements.txt`
  * `pyproject.toml`
  * `environment.yml`
  * `Dockerfile`
  * `package.xml`
  * `CMakeLists.txt`
* Parse Python dependencies from `requirements.txt`
* Check Python packages on PyPI
* Generate a basic installation plan
* Show basic system diagnostics:

  * OS
  * architecture
  * Python version
  * Git availability
  * Docker availability
  * NVIDIA GPU availability

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

Analyze a local repository:

```bash
simfix doctor ../simfix_test
```
```bash
simfix analyze ../simfix_test
```

To get the report
```bash
simfix doctor ../simfix_test --report
```
Generate an installation plan:

```bash
simfix plan ../simfix_test
```
Show suggested installation commands without running them:

```bash
simfix commands ../simfix_test
```
The usage section should now show:

```text
simfix system
simfix analyze <repo>
simfix plan <repo>
simfix doctor <repo>
simfix doctor <repo> --report
simfix version
simfix command
```
Analyze a GitHub repository:

```bash
simfix doctor https://github.com/hrehmaan/simfix.git
```

Show the installed version:

```bash
simfix version
```

## Example output

```text
SimFix Doctor
Repository: /path/to/repository

Detected dependency files
requirements.txt: yes
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
```

## Development checks

Run tests:

```bash
pytest
```

Run pre-commit:

```bash
pre-commit run --all-files
```

## Roadmap

Planned features:

* Better Python dependency parsing
* PyPI version compatibility checks
* Conda environment parsing
* Dockerfile analysis
* ROS dependency analysis with `rosdep`
* CMake dependency hints
* GPU/CUDA diagnostics
* Automatic report generation
* Safe installation commands for supported dependency types

## Project status

SimFix is in early development. At this stage, it focuses on diagnosis and installation planning rather than fully automatic installation.

The long-term goal is to make simulator setup easier by combining repository analysis, system diagnostics, dependency checks, and safe installation guidance.
