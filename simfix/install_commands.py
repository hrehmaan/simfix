"""Actionable install command generation for SimFix."""

from __future__ import annotations

from dataclasses import dataclass

from simfix.repo import RepoAnalysis


@dataclass(frozen=True)
class CommandGroup:
    """A group of related install commands."""

    title: str
    commands: tuple[str, ...]
    note: str | None = None


def generate_install_command_groups(analysis: RepoAnalysis) -> list[CommandGroup]:
    """Generate actionable install commands from detected repository metadata.

    The logic is generic and based on detected ecosystems/files, not repository names.
    """
    command_groups: list[CommandGroup] = []

    if analysis.has_dockerfile:
        command_groups.append(_docker_commands())

    if analysis.has_package_xml:
        command_groups.append(_ros_commands(analysis))

    if analysis.has_requirements_txt:
        command_groups.append(_python_requirements_commands())

    if analysis.has_pyproject_toml or analysis.has_setup_py:
        command_groups.append(_python_project_commands())

    if analysis.has_environment_yml:
        command_groups.append(_conda_commands())

    if analysis.has_cmake and not analysis.has_package_xml:
        command_groups.append(_cmake_commands())

    if not command_groups:
        command_groups.append(
            CommandGroup(
                title="Manual inspection",
                commands=(
                    "Read the project README installation section.",
                    "Check for install scripts such as install.sh, setup.sh, or Docker instructions.",
                    "Run project examples/tests after installing dependencies.",
                ),
                note="No common dependency files were detected.",
            )
        )

    return command_groups


def _docker_commands() -> CommandGroup:
    return CommandGroup(
        title="Docker workflow",
        commands=(
            "docker build -t simfix-workspace .",
            "./run_simfix_docker.sh",
        ),
        note=(
            "Use this when Dockerfile/run_simfix_docker.sh exists. "
            "For GPU projects, the host must have working NVIDIA Docker support."
        ),
    )


def _ros_commands(analysis: RepoAnalysis) -> CommandGroup:
    build_system = analysis.ros_package_info.build_system.lower()

    if build_system == "catkin":
        return CommandGroup(
            title="ROS 1 / catkin workflow",
            commands=(
                "rosdep update",
                "rosdep install --from-paths . --ignore-src -r -y",
                "catkin build",
                "source devel/setup.bash",
            ),
            note=(
                "Run these inside a ROS 1 workspace or inside the generated ROS Noetic Docker container."
            ),
        )

    if build_system in {"ament_cmake", "ament_python", "ament"}:
        return CommandGroup(
            title="ROS 2 / colcon workflow",
            commands=(
                "rosdep update",
                "rosdep install --from-paths . --ignore-src -r -y",
                "colcon build",
                "source install/setup.bash",
            ),
            note=(
                "Run these inside a ROS 2 workspace or inside a matching ROS 2 Docker container."
            ),
        )

    return CommandGroup(
        title="ROS workflow",
        commands=(
            "rosdep update",
            "rosdep install --from-paths . --ignore-src -r -y",
            "Build with catkin build or colcon build depending on the ROS package type.",
            "Source the generated setup file.",
        ),
        note="ROS package files were detected, but the build style was not classified.",
    )


def _python_requirements_commands() -> CommandGroup:
    return CommandGroup(
        title="Python requirements workflow",
        commands=(
            "python -m venv .venv",
            "source .venv/bin/activate",
            "python -m pip install --upgrade pip",
            "python -m pip install -r requirements.txt",
        ),
        note="Use this for repositories with requirements.txt.",
    )


def _python_project_commands() -> CommandGroup:
    return CommandGroup(
        title="Python editable install workflow",
        commands=(
            "python -m pip install -e .",
            "python -m pip install -e . --no-deps  # use only if vendor/manual dependencies block normal install",
        ),
        note=(
            "Use --no-deps only after installing normal requirements or when vendor dependencies "
            "must be installed manually."
        ),
    )


def _conda_commands() -> CommandGroup:
    return CommandGroup(
        title="Conda environment workflow",
        commands=(
            "conda env create -f environment.yml",
            "conda activate <environment-name>",
        ),
        note="Replace <environment-name> with the name defined inside environment.yml.",
    )


def _cmake_commands() -> CommandGroup:
    return CommandGroup(
        title="CMake workflow",
        commands=(
            "cmake -S . -B build",
            "cmake --build build",
        ),
        note="Use this for non-ROS CMake/C++ projects.",
    )
