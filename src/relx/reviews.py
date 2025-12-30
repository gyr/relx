import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from typing import Dict, Any

from relx.exceptions import RelxUserCancelError
from relx.providers import get_review_provider
from relx.providers.params import ObsListRequestsParams, Request
from relx.utils.logger import logger_setup
from relx.utils.tools import pager_command
# Removed: etree, run_command, running_spinner_decorator


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


# REMOVED: list_requests, show_request, approve_request functions


def show_request_list(requests: list[Request]) -> list[str]:
    lines = []
    if len(requests) == 0:
        lines.append("No pending reviews.")
    else:
        lines = [f"- SR#{request.id}: {request.name}" for request in requests]
    return lines


def build_parser(parent_parser, config: Dict[str, Any] | None) -> None:
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
        help="OBS/IBS project. Default is taken from config file.",
        type=str,
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
    Main method that handles review requests.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    console = Console()
    review_provider = get_review_provider(
        provider_name="obs", api_url=args.osc_instance
    )

    requests = []
    with console.status("[bold green]Fetching review requests..."):
        params = ObsListRequestsParams(  # Use ObsListRequestsParams here
            project=args.project,
            staging=args.staging,
            is_bugowner_request=args.bugowner,
        )
        requests = review_provider.list_requests(params)

    print_panel(show_request_list(requests), "Request Reviews")
    total_requests = len(requests)
    if total_requests == 0:
        return

    start_review = Prompt.ask(
        f">>> Start the reviews ({total_requests})?", choices=["y", "n"], default="y"
    )
    if start_review == "n":
        raise RelxUserCancelError("User cancelled at start.")

    for index, request in enumerate(requests, start=1):
        review_request = Prompt.ask(
            f">>> [{index}/{total_requests}] Review {request.id} - {request.name}?",
            choices=["y", "n", "a"],
            default="y",
        )
        if review_request == "y":
            with console.status(f"[bold green]Fetching diff for {request.id}..."):
                diff_content = review_provider.get_request_diff(request.id)
            pager_command(["delta"], diff_content)  # Use pager_command directly

            request_approval = Prompt.ask(
                f">>> Approve {request.id} - {request.name}?",
                choices=["y", "n", "a"],
                default="y",
            )
            if request_approval == "y":
                with console.status(f"[bold green]Approving {request.id}..."):
                    approval_lines = review_provider.approve_request(
                        request.id, args.bugowner
                    )
                print_panel(approval_lines)
            elif request_approval == "a":
                raise RelxUserCancelError("User aborted during approval.")
        elif review_request == "a":
            raise RelxUserCancelError("User aborted in main loop.")

    print_panel(["All reviews done."])
