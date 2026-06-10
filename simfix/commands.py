from __future__ import annotations

from dataclasses import dataclass

from simfix.analyzer import RepoAnalysis


@dataclass(frozen=True)
class CommandPlan:
    """Suggested shell commands for installing a repository."""

    title: str
    commands: list[str]


def create_command_plan(analysis: RepoAnalysis) -> CommandPlan:
    """Create suggested installation commands from repository analysis."""
    ecosystems = analysis.detected_ecosystems
    repo_name = analysis.repo_path.name.replace("_", "-").lower()
    commands: list[str] = []

    if "docker" in ecosystems:
        commands.append(f"docker build -t {repo_name} .")

        run_helper = analysis.repo_path / "run_simfix_docker.sh"
        if run_helper.exists():
            commands.append("./run_simfix_docker.sh")
        else:
            commands.append(f"docker run --rm -it {repo_name}")

    if "ros" in ecosystems:
        build_system = analysis.ros_package_info.build_system.lower()

        commands.extend(
            [
                "rosdep update",
                "rosdep install --from-paths . --ignore-src -r -y",
            ]
        )

        if build_system == "catkin":
            commands.extend(
                [
                    "catkin build",
                    "source devel/setup.bash",
                ]
            )
        elif build_system in {"ament", "ament_cmake", "ament_python"}:
            commands.extend(
                [
                    "colcon build",
                    "source install/setup.bash",
                ]
            )
        else:
            commands.extend(
                [
                    "catkin build  # or: colcon build, depending on the ROS package type",
                    "source devel/setup.bash  # or: source install/setup.bash",
                ]
            )

    if "conda" in ecosystems:
        env_name = "simfix-env"
        if analysis.conda_environment is not None and analysis.conda_environment.name:
            env_name = analysis.conda_environment.name

        commands.extend(
            [
                "conda env create -f environment.yml",
                f"conda activate {env_name}",
            ]
        )

    if "python" in ecosystems:
        commands.extend(
            [
                "python -m venv .venv",
                "source .venv/bin/activate",
                "python -m pip install --upgrade pip",
            ]
        )

        if analysis.has_requirements_txt:
            commands.append("python -m pip install -r requirements.txt")

        if analysis.has_pyproject_toml or analysis.has_setup_py:
            commands.extend(
                [
                    "python -m pip install -e .",
                    "python -m pip install -e . --no-deps  # use only if vendor/manual dependencies block normal install",
                ]
            )

    if "cmake/c++" in ecosystems and "ros" not in ecosystems:
        commands.extend(
            [
                "cmake -S . -B build",
                "cmake --build build -j",
            ]
        )

    if not commands:
        commands.extend(
            [
                "# No common dependency file was detected.",
                "# Read the README installation section manually.",
                "# Check for install scripts such as install.sh or setup.sh.",
            ]
        )

    return CommandPlan(
        title="Suggested installation commands",
        commands=_deduplicate_commands(commands),
    )


def _deduplicate_commands(commands: list[str]) -> list[str]:
    """Return commands without duplicates while preserving order."""
    seen: set[str] = set()
    unique_commands: list[str] = []

    for command in commands:
        if command in seen:
            continue

        seen.add(command)
        unique_commands.append(command)

    return unique_commands
