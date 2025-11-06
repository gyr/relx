from bs4 import BeautifulSoup
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from subprocess import CalledProcessError
from typing import Generator

from relx.utils.logger import logger_setup
from relx.utils.tools import (
    run_command,
    running_spinner_decorator,
)


log = logger_setup(__name__)


@running_spinner_decorator
def get_groups(api_url: str, group: str, is_fulllist: bool = False) -> dict:
    """
    Given a group name return the OBS info about it."

    :param api_url: OBS instance
    :param group: OBS group name
    :return: OBS group info
    """
    try:
        command = f"osc -A {api_url} api /group/{group}"
        output = run_command(command.split())
        soup = BeautifulSoup(output.stdout, "lxml")
        info = {}

        title = soup.find("title")
        info["Group"] = title.text if title else None

        email = soup.find("email")
        info["Email"] = email.text if email else None

        maintainers = soup.find_all("maintainer")
        info["Maintainers"] = [tag["userid"] for tag in maintainers]

        if is_fulllist:
            people = soup.find_all("person")
            info["Users"] = [
                person.get("userid") for person in people if person.get("userid")
            ]

        return info
    except CalledProcessError as e:
        raise RuntimeError(f"{group} not found.") from e


@running_spinner_decorator
def get_users(
    api_url: str,
    search_text: str,
    is_login: bool = True,
    is_email: bool = False,
    is_realname: bool = False,
) -> Generator:
    """
    Given a source package return the OBS user of the bugowner"

    :param api_url: OBS instance
    :param search_text: Text to be search OBS project for user info
    :param is_login: Search based on user login
    :param is_email: Search based on user email
    :param is_realname: Search based on user name
    :return: OBS user info
    """
    try:
        if is_login:
            command = (
                f'osc -A {api_url} api /search/person?match=@login="{search_text}"'
            )
        elif is_email:
            command = (
                f'osc -A {api_url} api /search/person?match=@email="{search_text}"'
            )
        elif is_realname:
            command = f'osc -A {api_url} api /search/person?match=contains(@realname,"{search_text}")'
        else:
            raise RuntimeError("Invalid user search.")

        output = run_command(command.split())
        soup = BeautifulSoup(output.stdout, "lxml")
        info = {}
        people = soup.find_all("person")
        if not people:
            raise RuntimeError(f"{search_text} not found.")
        for person in people:
            info = {
                "User": person.find("login").text,
                "Email": person.find("email").text,
                "Name": person.find("realname").text,
                "State": person.find("state").text,
            }
            yield info
    except CalledProcessError as e:
        raise RuntimeError(f"{search_text} not found.") from e


def build_parser(parent_parser, config) -> None:
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
    Main method that get the OBS user from the bugowner for the given binary package.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    console = Console()
    try:
        table = Table(show_header=False)
        if args.group:
            for key, value in get_groups(
                args.osc_instance, args.search_text, True
            ).items():
                log.debug("%s: %s", key, value)
                table.add_row(key, str(value))
        else:
            for info in get_users(
                args.osc_instance, args.search_text, args.login, args.email, args.name
            ):
                for key, value in info.items():
                    log.debug("%s: %s", key, value)
                    table.add_row(key, str(value))
                table.add_row(Rule(style="dim"), Rule(style="dim"))
        console.print(table)
    except RuntimeError as e:
        log.error(e)
