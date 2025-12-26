#!/usr/bin/env python3
import argparse
import importlib
import os
import sys
import urllib.error
import yaml

import argcomplete
from dotenv import load_dotenv
from typing import Dict, Any

from relx import __version__
from relx.exceptions import (
    RelxResourceNotFoundError,
    RelxUserCancelError,
)
from relx.utils.logger import logger_setup, global_logger_config

# --- Configuration ---
# Explicitly load .env from the project root for developer convenience.
# This is safer than a broad search and does nothing if the .env file doesn't exist.
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=dotenv_path)

relx_conf_dir = os.environ.get("RELX_CONF_DIR")

if relx_conf_dir:
    # Expand user (~) if present in the env var path
    config_dir = os.path.expanduser(relx_conf_dir)
else:
    # Default to XDG_CONFIG_HOME/relx or ~/.config/relx
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    config_dir = os.path.join(xdg_config_home, "relx")

config_file_path = os.path.join(config_dir, "config.yaml")


def load_config(config_file_path: str) -> Dict[str, Any]:
    try:
        with open(config_file_path, "r") as f:
            config = yaml.safe_load(f)
        return config
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


config = load_config(config_file_path)

PARSER = argparse.ArgumentParser(description="Release management tools.")
PARSER.add_argument(
    "--osc-config",
    dest="osc_config",
    help="The location of the oscrc if a specific one should be used.",
)
PARSER.add_argument(
    "--osc-instance",
    dest="osc_instance",
    help=f"The URL of the API from the Open Buildservice instance that should be used (DEFAULT = {config['api_url']}).",
    default=config["api_url"],
)
PARSER.add_argument(
    "--debug",
    "-d",
    action="store_true",
    help="Enable debug logging.",
)
PARSER.add_argument(
    "--version",
    action="version",
    version=f"%(prog)s {__version__}",
)
SUBPARSERS = PARSER.add_subparsers(
    help="Help for the subprograms that this tool offers."
)


log = logger_setup(__name__)


def import_sle_module(name: str) -> None:
    """
    Imports a module

    :param name: Module in the relx package.
    """
    module = importlib.import_module(f".{name}", package="relx")
    module.build_parser(SUBPARSERS, config)


def main() -> None:
    # --- Dynamic Module Discovery ---
    module_list = []
    # Get the directory of the 'relx' package
    package_path = os.path.dirname(os.path.abspath(__file__))

    for name in os.listdir(package_path):
        # Check if it's a python file and not a special/internal module
        if name.endswith(".py") and not name.startswith("__"):
            module_name = name[:-3]  # Remove .py extension

            # Exclude specific modules and directories that are not subcommands
            if module_name in ["cli", "exceptions", "requests"]:
                continue

            module_list.append(module_name)

    module_list.sort()  # Sort for deterministic order
    # --- End Discovery ---

    for module in module_list:
        import_sle_module(module)
    argcomplete.autocomplete(PARSER)
    args = PARSER.parse_args()
    global_logger_config(verbose=args.debug or config["debug"])
    log.debug(f"{config_dir=}")
    if "func" in vars(args):
        # Run a subprogramm only if the parser detected it correctly.
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
        return
    PARSER.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
