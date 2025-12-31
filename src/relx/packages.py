from rich.console import Console
from rich.table import Table
from typing import Dict, Any
from argparse import Namespace

from relx.providers import (
    get_user_provider,
    get_package_provider,
    UserProvider,
    PackageProvider,
)
from relx.utils.logger import logger_setup


log = logger_setup(__name__)


def build_parser(parent_parser, config: Dict[str, Any] | None) -> None:
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
        help="OBS/IBS project. Default is taken from config file.",
        type=str,
    )
    subparser.add_argument(
        "--product",
        "-P",
        dest="product",
        help="OBS/IBS product. Default is taken from config file.",
        type=str,
    )
    subparser.add_argument("binary_name", nargs="+", type=str, help="Binary name.")
    subparser.set_defaults(func=main)


def main(args: Namespace, config: Dict[str, Any]) -> None:
    """
    Main method that gets OBS user from the bugowner for the given binary package.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    console = Console()
    package_provider = get_package_provider(
        provider_name="obs", api_url=args.osc_instance
    )
    user_provider = get_user_provider(provider_name="obs", api_url=args.osc_instance)

    for binary in args.binary_name:
        try:
            _process_single_package(
                binary, args, config, console, package_provider, user_provider
            )
        except RuntimeError as e:
            log.error(e)
            console.print(f"[bold red]Error:[/bold red] {e}")
        except Exception as e:
            log.error(e)
            console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")


def _process_single_package(
    binary: str,
    args: Namespace,
    config: Dict[str, Any],
    console: Console,
    package_provider: PackageProvider,
    user_provider: UserProvider,
) -> None:
    """
    Processes a single binary package, fetches its information, and prints it.
    """
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
        bugowners, is_group = package_provider.get_bugowner(package=source_package)

    table.add_row("Source package", source_package)
    if shipped:
        table.add_row("Shipped", f"YES - {args.product}")
    else:
        table.add_row("Shipped", "*** NO ***")

    for bugowner in bugowners:
        for key, value in user_provider.get_entity_info(
            name=bugowner, is_group=is_group
        ).items():
            log.debug("%s: %s", key, value)
            table.add_row(key, str(value))
    console.print(table)
