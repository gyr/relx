from rich.console import Console
from rich.table import Table
from typing import Dict, Any

from relx.providers import get_user_provider, get_package_provider
from relx.utils.logger import logger_setup
# Removed: re, lxml, etree, CalledProcessError, run_command, run_command_and_stream_output, running_spinner_decorator


log = logger_setup(__name__)


# REMOVED: is_shipped, get_source_package, get_bugowner functions


def get_bugowner_info(api_url: str, user: str, is_group: bool) -> dict:
    """
    Given a bugowner, return their OBS info.
    :param api_url: OBS instance
    :param user: bugowner name (user or group)
    :param is_group: True if the bugowner is a group
    :return: OBS info dictionary
    """
    user_provider = get_user_provider(provider_name="obs", api_url=api_url)
    try:
        if is_group:
            return user_provider.get_group(user, is_fulllist=False)
        else:
            user_iterator = user_provider.get_user(search_text=user, search_by="login")
            return next(user_iterator)
    except (RuntimeError, StopIteration) as e:
        raise RuntimeError(f"Bugowner '{user}' not found.") from e


def build_parser(parent_parser, config: Dict[str, Any]) -> None:
    """
    Builds the parser for this script. This is executed by the main CLI
    dynamically.

    :param config: Lua config table
    :return: The subparsers object from argparse.
    """
    subparser = parent_parser.add_parser(
        "packages",
        help="Return OBS information for the given binary package.",
    )
    subparser.add_argument(
        "--project",
        "-p",
        dest="project",
        help=f"OBS/IBS project (DEFAULT = {config['default_project']}).",
        type=str,
        default=config["default_project"],
    )
    subparser.add_argument(
        "--product",
        "-P",
        dest="product",
        help=f"OBS/IBS product (DEFAULT = {config['default_product']}).",
        type=str,
        default=config["default_product"],
    )
    subparser.add_argument("binary_name", nargs="+", type=str, help="Binary name.")
    subparser.set_defaults(func=main)


def main(args, config: Dict[str, Any]) -> None:
    """
    Main method that get the OBS user from the bugowner for the given binary package.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    console = Console()
    package_provider = get_package_provider(
        provider_name="obs", api_url=args.osc_instance
    )

    for binary in args.binary_name:
        try:
            table = Table(title=binary, show_header=False)

            with console.status(f"[bold green]Fetching info for {binary}..."):
                source_package = package_provider.get_source_package(
                    project=args.project, package=binary
                )

                shipped = package_provider.is_shipped(
                    package=binary,
                    productcomposer=config["default_product"]
                    + config["default_productcomposer"],
                )
                bugowners, is_group = package_provider.get_bugowner(
                    package=source_package
                )

            table.add_row("Source package", source_package)
            if shipped:
                table.add_row("Shipped", f"YES - {args.product}")
            else:
                table.add_row("Shipped", "*** NO ***")

            for bugowner in bugowners:
                for key, value in get_bugowner_info(
                    args.osc_instance, bugowner, is_group
                ).items():
                    log.debug("%s: %s", key, value)
                    table.add_row(key, str(value))
            console.print(table)
        except RuntimeError as e:
            log.error(e)
            console.print(f"[bold red]Error:[/bold red] {e}")
            # Do not exit here, allow processing of other binaries if any
        except Exception as e:
            log.error(e)
            console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
            # Do not exit here, allow processing of other binaries if any
