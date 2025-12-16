import argparse
import sys
from lxml import etree
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from typing import Dict, Any

from relx.utils.logger import logger_setup
from relx.utils.tools import (
    pager_command,
    run_command,
    running_spinner_decorator,
)


log = logger_setup(__name__)


def valid_staging(staging: str) -> str:
    """
    Validate if a string is a single letter.

    :param staging: string to check
    :return evaluated string
    """
    try:
        if len(staging) != 1 or not staging.isalpha():
            msg = "Staging must be a single letter"
            raise argparse.ArgumentTypeError(msg)
        return staging
    except ValueError as exc:
        msg = f"Not a valid staging: '{staging}'. Must a single letter."
        raise argparse.ArgumentTypeError(msg) from exc


def print_panel(lines: list[str], title: str = "") -> None:
    console = Console()
    panel_content = "\n".join(lines)
    panel = Panel(panel_content, title=title)
    console.print(panel)


@running_spinner_decorator
def list_requests(
    api_url: str, project: str, staging: str = None, is_bugowner_request: bool = False
) -> list[tuple[str, str]]:
    """
    List all source packages from a OBS project

    :param api_url: OBS instance
    :param project: OBS project
    :param is_bugowner_request: list bugowner requests
    :return: list of source packages
    """
    command = f"osc -A {api_url} api".split()
    if is_bugowner_request:
        command.append(
            f"/search/request?match=state/@name='review' and action/@type='set_bugowner' and action/target/@project='{project}'&withhistory=0&withfullhistory=0"
        )
    elif staging:
        project = f"{project}:Staging:{staging}"
        command.append(
            f"/search/request?match=state/@name='review' and review/@state='new' and review/@by_project='{project}'&withhistory=0&withfullhistory=0"
        )
    else:
        command.append(
            f"/search/request?match=state/@name='review' and review/@state='new' and target/@project='{project}'&withhistory=0&withfullhistory=0"
        )
    result = run_command(command)

    tree = etree.fromstring(result.stdout.encode())

    requests = []

    for request in tree.findall("request"):
        state_tag = request.find("state")
        if state_tag is not None and state_tag.get("name") == "review":
            relmgr_review = request.find("review[@by_group='sle-release-managers']")
            if relmgr_review is not None and relmgr_review.get("state") == "new":
                request_tuple = (
                    request.get("id"),
                    request.find("action/target").get("package"),
                )
                log.debug(f"{request_tuple=}")
                requests.append(request_tuple)
    return requests


def show_request(api_url: str, request: str) -> None:
    """
    Show reviewed request details

    :param api_url: OBS instance
    :param request: request ID
    """
    command = f"osc -A {api_url} review show -d {request}"
    output = run_command(command.split())
    pager_command(["delta"], output.stdout)


@running_spinner_decorator
def approve_request(api_url: str, request: str, is_bugowner: bool) -> list[str]:
    """
    Approve request

    :param api_url: OBS instance
    :param request: request ID
    :param bugowner: is a bugowner request
    """
    groups: list = ["sle-release-managers"]
    lines = []
    if is_bugowner:
        groups.append("sle-staging-managers")
    for group in groups:
        command = f"osc -A {api_url} review accept -m 'OK' -G {group} {request}"
        output = run_command(command.split())
        lines.append(f"{group}: {output.stdout}")
    return lines


def show_request_list(requests: list[tuple[str, str]]) -> list[str]:
    lines = []
    if len(requests) == 0:
        lines.append("No pending reviews.")
    else:
        lines = [f"- SR#{id}: {package}" for id, package in requests]
    return lines


def build_parser(parent_parser, config: Dict[str, Any]) -> None:
    """
    Builds the parser for this script. This is executed by the main CLI
    dynamically.

    :param config: Lua config table
    :return: The subparsers object from argparse.
    """
    subparser = parent_parser.add_parser(
        "reviews", help="Review submit, delete and bugowner requests."
    )
    subparser.add_argument(
        "--project",
        "-p",
        dest="project",
        help=f"OBS/IBS project (DEFAULT = {config['default_project']}).",
        type=str,
        default=config["default_project"],
    )
    # Mutually exclusive group within the subparser
    group = subparser.add_mutually_exclusive_group()
    group.add_argument(
        "--staging", "-s", dest="staging", type=valid_staging, help="Staging letter."
    )
    group.add_argument(
        "--bugowner", "-b", action="store_true", help="Review bugowner requests."
    )
    subparser.set_defaults(func=main)


def main(args, config: Dict[str, Any]) -> None:
    """
    Main method that get the list of all artifacts from a given OBS project

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    requests = []
    # Parse arguments
    requests = list_requests(
        args.osc_instance, args.project, args.staging, args.bugowner
    )

    print_panel(show_request_list(requests), "Request Reviews")
    total_requests = len(requests)
    if total_requests == 0:
        sys.exit(0)

    start_review = Prompt.ask(
        f">>> Start the reviews ({total_requests})?", choices=["y", "n"], default="y"
    )
    if start_review == "n":
        sys.exit(0)

    for index, request in enumerate(requests, start=1):
        review_request = Prompt.ask(
            f">>> [{index}/{total_requests}] Review {request[0]} - {request[1]}?",
            choices=["y", "n", "a"],
            default="y",
        )
        if review_request == "y":
            show_request(args.osc_instance, request[0])
            request_approval = Prompt.ask(
                f">>> Approve {request[0]} - {request[1]}?",
                choices=["y", "n", "a"],
                default="y",
            )
            if request_approval == "y":
                print_panel(
                    approve_request(args.osc_instance, request[0], args.bugowner)
                )
        elif review_request == "a":
            sys.exit(0)

    print_panel(["All reviews done."])
