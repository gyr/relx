import re
from argparse import Namespace
from rich.progress import Progress, TaskID
from typing import Dict, Any

from relx.utils.logger import logger_setup
from relx.utils.tools import (
    run_command,
    run_command_and_stream_output,
    running_spinner_decorator,
)


log = logger_setup(__name__)


@running_spinner_decorator
def list_packages(api_url: str, project: str) -> list[str]:
    """
    List all source packages from a OBS project

    :param api_url: OBS instance
    :param project: OBS project
    :return: list of source packages
    """
    command = f"osc -A {api_url} ls {project}"
    output = run_command(command.split())
    return output.stdout


def list_artifacs(
    api_url: str,
    project: str,
    packages: list[str],
    invalid_start: list[str],
    invalid_extensions: list[str],
    repo_info: Dict[str, str],
    progress: Progress,
    task_id: TaskID,
) -> None:
    """
    List all artifacts filtered by pattern in the specified repoistory
    from a OBS project

    :param api_url: OBS instance
    :param project: OBS project
    :param project: list of source packages
    :param repo_info: Lua Table with repository info
    """
    log.debug(">> pattern = %s", repo_info["pattern"])
    pattern = re.compile(repo_info["pattern"])
    log.debug(">> pattern = %s", pattern)

    for package in packages:
        if re.search(pattern, package):
            command = [
                "/bin/bash",
                "-c",
                f"osc -A {api_url} ls {project} {package} -b -r {repo_info['name']}",
            ]
            for line in run_command_and_stream_output(command):
                if not line.startswith(tuple(invalid_start)) and not line.startswith(
                    f"{repo_info['name']}/"
                ):
                    if not line.endswith(tuple(invalid_extensions)):
                        print(line)
        progress.update(task_id, advance=1)


def build_parser(parent_parser, config: Dict[str, Any]) -> None:
    """
    Builds the parser for this script. This is executed by the main CLI
    dynamically.

    :param config: Lua config table
    :return: The subparsers object from argparse.
    """
    subparser = parent_parser.add_parser(
        "artifacts", help="Return the list of artifacts from a OBS project."
    )
    subparser.add_argument(
        "--project",
        "-p",
        dest="project",
        help=f"OBS/IBS project (DEFAULT = {config['default_product']}).",
        type=str,
        default=config["default_product"],
    )
    subparser.set_defaults(func=main)


def main(args: Namespace, config: Dict[str, Any]) -> None:
    """
    Main method that get the list of all artifacts from a given OBS project

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    # Parse arguments
    parameters = {"api_url": args.osc_instance, "project": args.project}
    packages = list_packages(**parameters).split()

    parameters.update(
        {
            "packages": packages,
        }
    )
    total_steps = len(config["artifacts"]["repo_info"]) * len(packages)
    with Progress() as progress:
        task_id = progress.add_task("Searching artifacts", total=total_steps)
        for repo_info in config["artifacts"]["repo_info"]:
            parameters.update(
                {
                    "invalid_start": config["artifacts"]["invalid_start"],
                    "invalid_extensions": config["artifacts"]["invalid_extensions"],
                    "repo_info": repo_info,
                    "progress": progress,
                    "task_id": task_id,
                }
            )
            list_artifacs(**parameters)
