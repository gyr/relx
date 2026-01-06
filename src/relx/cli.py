#!/usr/bin/env python3
import argparse
import importlib
import os
import sys
import urllib.error
from pathlib import Path
from typing import Any, Dict

import argcomplete
import yaml
from dotenv import load_dotenv

from relx import __version__
from relx.exceptions import RelxResourceNotFoundError, RelxUserCancelError
from relx.utils.logger import global_logger_config, logger_setup

log = logger_setup(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Creates the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="relx", description="Release management tools."
    )
    parser.add_argument(
        "--osc-config",
        dest="osc_config",
        help="The location of the oscrc if a specific one should be used.",
    )
    parser.add_argument(
        "--osc-instance",
        dest="osc_instance",
        help="The URL of the API from the Open Buildservice instance.",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def load_all_modules(parser: argparse.ArgumentParser) -> None:
    """Dynamically discovers and loads all subcommand modules."""
    subparsers = parser.add_subparsers(
        title="positional arguments",
        help="Help for the subprograms that this tool offers.",
    )
    package_path = Path(__file__).parent.resolve()
    module_names = []

    for path in package_path.iterdir():
        if (
            path.is_file()
            and path.name.endswith(".py")
            and not path.name.startswith("__")
        ):
            module_name = path.name[:-3]
            if module_name not in ["cli", "exceptions", "requests"]:
                module_names.append(module_name)

    module_names.sort()

    for module_name in module_names:
        module = importlib.import_module(f".{module_name}", package="relx")
        # Pass None for config, as it's not needed to build the parsers.
        module.build_parser(subparsers, None)


def get_config_path() -> str:
    """Determines the path to the configuration file."""
    project_root = Path(__file__).resolve().parents[2]
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)

    relx_conf_dir = os.environ.get("RELX_CONF_DIR")
    if relx_conf_dir:
        config_dir = Path(relx_conf_dir).expanduser()
    else:
        xdg_config_home = Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        )
        config_dir = xdg_config_home / "relx"

    return str(config_dir / "config.yaml")


def load_config(config_file_path: str) -> Dict[str, Any]:
    """Loads the YAML configuration file or exits if not found."""
    try:
        with open(config_file_path, "r") as f:
            config = yaml.safe_load(f)
            return config or {}
    except FileNotFoundError:
        print(
            f"Error: Configuration file '{config_file_path}' not found.",
            file=sys.stderr,
        )
        sys.exit(1)
    except yaml.YAMLError as e:
        print(
            f"Error: Invalid YAML format in '{config_file_path}': {e}", file=sys.stderr
        )
        sys.exit(1)


def main() -> None:
    """The main entry point for the relx CLI."""
    parser = create_parser()
    # Load all subcommands so they are available for help messages.
    load_all_modules(parser)
    argcomplete.autocomplete(parser)

    # This parse will handle --version and --help (and exit), and also
    # identify which subcommand (if any) was used.
    args = parser.parse_args()

    # If no subcommand was provided, argparse will not set the 'func' attribute.
    # In this case, print help and exit. Argparse handles the -h/--help case itself.
    if "func" not in vars(args):
        parser.print_help()
        sys.exit(1)

    # --- A subcommand was specified, so now we need the config ---
    config_path = get_config_path()
    config = load_config(config_path)

    # Apply defaults from config if they weren't provided on the command line.
    # The command-line argument (if given) always takes precedence.
    if args.osc_instance is None and "api_url" in config:
        args.osc_instance = config["api_url"]
    if args.debug is False and "debug" in config:
        args.debug = config["debug"]

    # Set defaults for subcommand-specific arguments
    if "product" in args and args.product is None:
        args.product = config.get("default_product")

    # Update the config with the final values from args to pass to functions.
    config["api_url"] = args.osc_instance
    config["debug"] = args.debug

    global_logger_config(verbose=args.debug)
    log.debug(f"Using config file: {config_path}")

    # --- Execute subcommand ---
    try:
        args.func(args, config)
    except RelxUserCancelError as e:
        log.info(f"User cancelled operation. {e}")
        print("Operation cancelled by user.", file=sys.stderr)
        sys.exit(0)
    except (RelxResourceNotFoundError, RuntimeError) as e:
        log.error(e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as url_error:
        if "name or service not known" in str(url_error).lower():
            log.error(
                "No connection to one of the tools. Please make sure the "
                "connection to the tools is available before executing "
                "the program!"
            )
            sys.exit(1)
        # Re-raise other URL errors
        raise


if __name__ == "__main__":
    main()
