from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from typing import Dict, Any

from relx.exceptions import RelxResourceNotFoundError
from relx.utils.logger import logger_setup
from relx.providers import get_user_provider


log = logger_setup(__name__)


def build_parser(parent_parser, config: Dict[str, Any] | None) -> None:
    """
    Builds the parser for this script. This is executed by the main CLI
    dynamically.

    :param config: Lua config table
    :return: The subparsers object from argparse.
    """
    subparser = parent_parser.add_parser(
        "users",
        help="Search in OBS information for the given user/group.",
    )
    # Mutually exclusive group within the subparser
    group = subparser.add_mutually_exclusive_group(required=True)
    group.add_argument("--group", "-g", action="store_true", help="Search for group.")
    group.add_argument(
        "--login", "-l", action="store_true", help="Search user for login."
    )
    group.add_argument(
        "--email", "-e", action="store_true", help="Search user for email."
    )
    group.add_argument(
        "--name", "-n", action="store_true", help="Search user for name."
    )
    subparser.add_argument("search_text", type=str, help="Search text.")
    subparser.set_defaults(func=main)


def main(args, config) -> None:
    """
    Main method that gets OBS user/group information using the UserProvider.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    console = Console()
    user_provider = get_user_provider(provider_name="obs", api_url=args.osc_instance)
    table = Table(show_header=False)

    with console.status("[bold green]Running..."):
        if args.group:
            group_info = user_provider.get_group(
                group=args.search_text, is_fulllist=True
            )
            if not group_info:
                raise RelxResourceNotFoundError(
                    f"Group '{args.search_text}' not found."
                )
            for key, value in group_info.items():
                log.debug("%s: %s", key, value)
                table.add_row(key, str(value))
        else:
            search_by = ""
            if args.login:
                search_by = "login"
            elif args.email:
                search_by = "email"
            elif args.name:
                search_by = "realname"

            user_results = list(
                user_provider.get_user(
                    search_text=args.search_text, search_by=search_by
                )
            )

            if not user_results:
                raise RelxResourceNotFoundError(f"User '{args.search_text}' not found.")

            for info in user_results:
                for key, value in info.items():
                    log.debug("%s: %s", key, value)
                    table.add_row(key, str(value))
                table.add_row(Rule(style="dim"), Rule(style="dim"))

    console.print(table)
