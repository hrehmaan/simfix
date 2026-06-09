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

    if "docker" in ecosystems:
        return CommandPlan(
            title="Docker installation commands",
            commands=[
                f"docker build -t {repo_name} .",
                f"docker run --rm -it {repo_name}",
            ],
        )

    if "conda" in ecosystems:
        env_name = "simfix-env"
        if analysis.conda_environment is not None and analysis.conda_environment.name:
            env_name = analysis.conda_environment.name

        return CommandPlan(
            title="Conda installation commands",
            commands=[
                "conda env create -f environment.yml",
                f"conda activate {env_name}",
            ],
        )

    if "ros" in ecosystems:
        return CommandPlan(
            title="ROS installation commands",
            commands=[
                "mkdir -p ~/simfix_ws/src",
                "cd ~/simfix_ws/src",
                "# Clone or copy the repository into this src folder",
                "cd ~/simfix_ws",
                "rosdep install --from-paths src --ignore-src -r -y",
                "catkin build  # or: colcon build",
                "source devel/setup.bash  # or: source install/setup.bash",
            ],
        )

    if "python" in ecosystems:
        commands = [
            "python -m venv .venv",
            "source .venv/bin/activate",
        ]

        if analysis.has_requirements_txt:
            commands.append("python -m pip install -r requirements.txt")

        if analysis.has_pyproject_toml:
            commands.append("python -m pip install -e .")

        return CommandPlan(
            title="Python installation commands",
            commands=commands,
        )

    if "cmake/c++" in ecosystems:
        return CommandPlan(
            title="CMake installation commands",
            commands=[
                "mkdir -p build",
                "cd build",
                "cmake ..",
                "cmake --build . -j",
            ],
        )

    return CommandPlan(
        title="Manual installation commands",
        commands=[
            "# No common dependency file was detected.",
            "# Read the README installation section manually.",
        ],
    )
