import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from typing import Dict, Any

from relx.exceptions import RelxUserCancelError
from relx.providers import get_review_provider
from relx.providers.params import (
    ListRequestsParams,
    ObsListRequestsParams,
    GiteaListRequestsParams,
    Request,
    GetRequestDiffParams,
    ObsGetRequestDiffParams,
    GiteaGetRequestDiffParams,
)
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
        for request in requests:
            prefix = "PR#" if request.provider_type == "gitea" else "SR#"
            lines.append(f"- {prefix}{request.id}: {request.name}")
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

    # OBS Arguments
    obs_group = subparser.add_argument_group("OBS Provider Arguments")
    obs_group.add_argument(
        "--project",
        "-p",
        dest="project",
        help="OBS/IBS project. Required for OBS provider.",
        type=str,
    )
    obs_exclusive_group = obs_group.add_mutually_exclusive_group()
    obs_exclusive_group.add_argument(
        "--staging", "-s", dest="staging", type=valid_staging, help="Staging letter."
    )
    obs_exclusive_group.add_argument(
        "--bugowner",
        "-b",
        dest="bugowner",
        action="store_true",
        help="Review bugowner requests.",
    )

    # Gitea Arguments
    gitea_group = subparser.add_argument_group("Gitea Provider Arguments")
    gitea_group.add_argument(
        "--repository", dest="repository", help="Gitea repository."
    )
    gitea_group.add_argument("--branch", dest="branch", help="Gitea target branch.")
    gitea_group.add_argument("--reviewer", dest="reviewer", help="Gitea reviewer.")
    gitea_group.add_argument(
        "--prs",
        dest="prs",
        help="Comma-separated list of PR IDs to filter by.",
        type=str,
    )

    subparser.set_defaults(func=main)


def main(args, config: Dict[str, Any]) -> None:
    """
    Main method that handles review requests.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    console = Console()

    is_obs = args.project is not None
    is_gitea = all([args.repository, args.branch, args.reviewer])

    # Enforce mutual exclusivity
    if is_obs and is_gitea:
        console.print(
            "[bold red]Error: Please provide arguments for either OBS (--project) or Gitea, not both.[/bold red]"
        )
        return

    # Enforce dependency of staging/bugowner on project
    if (args.staging is not None or args.bugowner) and not is_obs:
        console.print(
            "[bold red]Error: --project is required when using --staging or --bugowner.[/bold red]"
        )
        return

    # Enforce dependency of prs on gitea
    if args.prs and not is_gitea:
        console.print(
            "[bold red]Error: --prs can only be used with Gitea arguments (--repository, --branch, --reviewer).[/bold red]"
        )
        return

    # Validate --prs value early if it's provided with Gitea args
    if is_gitea and args.prs:
        try:
            # We parse it here just for validation. The actual filtering happens later.
            _ = {int(pr_id.strip()) for pr_id in args.prs.split(",")}
        except ValueError:
            console.print(
                "[bold red]Error: --prs must be a comma-separated list of numbers.[/bold red]"
            )
            return

    params: ListRequestsParams
    if is_gitea:
        provider_name = "gitea"
        params = GiteaListRequestsParams(
            repository=args.repository,
            branch=args.branch,
            reviewer=args.reviewer,
        )
    elif is_obs:
        provider_name = "obs"
        params = ObsListRequestsParams(
            project=args.project,
            staging=args.staging,
            is_bugowner_request=args.bugowner,
        )
    else:
        console.print(
            "[bold red]Error: Please provide arguments for a provider. For OBS: --project. For Gitea: --repository, --branch, AND --reviewer.[/bold red]"
        )
        return

    review_provider = get_review_provider(
        provider_name=provider_name, api_url=args.osc_instance
    )

    requests = []
    with console.status("[bold green]Fetching review requests..."):
        all_requests = review_provider.list_requests(params)

    if args.prs and is_gitea:
        try:
            requested_pr_ids = {int(pr_id.strip()) for pr_id in args.prs.split(",")}
        except ValueError:
            console.print(
                "[bold red]Error: --prs must be a comma-separated list of numbers.[/bold red]"
            )
            return

        requests = [req for req in all_requests if int(req.id) in requested_pr_ids]
        found_pr_ids = {int(req.id) for req in requests}
        not_found_ids = requested_pr_ids - found_pr_ids
        if not_found_ids:
            console.print(
                f"[bold yellow]Warning: The following PRs were not found: {', '.join(map(str, not_found_ids))}[/bold yellow]"
            )
    else:
        requests = all_requests

    print_panel(
        show_request_list(requests), f"Request Reviews for {provider_name.upper()}"
    )
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
                diff_params: GetRequestDiffParams
                if is_gitea:
                    diff_params = GiteaGetRequestDiffParams(
                        request_id=request.id, repository=args.repository
                    )
                else:  # is_obs
                    diff_params = ObsGetRequestDiffParams(request_id=request.id)
                diff_content = review_provider.get_request_diff(diff_params)
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
