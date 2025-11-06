#!/usr/bin/env python3
import argparse
import importlib
import os
import sys
import urllib.error

import argcomplete
from dotenv import load_dotenv
from lupa import LuaRuntime  # type: ignore

from relx import __version__
from relx.utils.logger import logger_setup, global_logger_config

# Get the directory of config.lua
load_dotenv()
config_dir = os.environ.get("CONFIG_DIR")
if config_dir is None:
    config_dir = os.path.expanduser("~/.config/relx")

# Load the Lua runtime and modify the package path
# lua = lupa.LuaRuntime()
lua = LuaRuntime()
lua.execute(f'package.path = package.path .. ";{config_dir}/?.lua"')

# Now you can require "config" (without the full path)
# it will return a tuple: lua table and full path to config file
config, _ = lua.require("config")

PARSER = argparse.ArgumentParser(description="Release management tools.")
PARSER.add_argument(
    "--osc-config",
    dest="osc_config",
    help="The location of the oscrc if a specific one should be used.",
)
PARSER.add_argument(
    "--osc-instance",
    dest="osc_instance",
    help="The URL of the API from the Open Buildservice instance that should be used.",
    default=config.common.api_url,
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
    module_list = ["artifacts", "requests", "reviews", "packages", "users"]
    for module in module_list:
        import_sle_module(module)
    argcomplete.autocomplete(PARSER)
    args = PARSER.parse_args()
    global_logger_config(verbose=args.debug or config.common.debug)
    log.debug(f"{config_dir=}")
    if "func" in vars(args):
        # Run a subprogramm only if the parser detected it correctly.
        try:
            args.func(args, config)
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
