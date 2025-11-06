import argparse
import datetime

from relx.utils.logger import logger_setup
from relx.utils.tools import (
    count_days,
    run_command_and_stream_output,
    running_spinner_decorator,
)


log = logger_setup(name=__name__)


def valid_days(days: str) -> str:
    """
    Validate if string date is in the format YYYY-MM-DD to be used in argparse
    """
    try:
        if int(days) <= 0:
            msg = "Days must be a nonzero positive number."
            raise argparse.ArgumentTypeError(msg)
        return days
    except ValueError as exc:
        msg = f"Not a valid days: '{days}'. Must a nonzero positive number."
        raise argparse.ArgumentTypeError(msg) from exc


def valid_date(string_date: str) -> datetime.date:
    """
    Validate if string date is in the format YYYY-MM-DD to be used in argparse
    """
    try:
        formated_date = datetime.datetime.strptime(string_date, "%Y-%m-%d").date()
        if formated_date >= datetime.date.today():
            msg = f"Date {formated_date} is in the future."
            raise argparse.ArgumentTypeError(msg)
        return formated_date
    except ValueError as exc:
        msg = f"Not a valid date: '{string_date}'.  Use YYYY-MM-DD format."
        raise argparse.ArgumentTypeError(msg) from exc


@running_spinner_decorator
def list_requests(
    api_url: str, project: str, request_type: str, time_period: str = ""
) -> None:
    """
    List all requests accpeted on OBS project

    :param api_url: OBS instance
    :param project: OBS project
    :param request_type: submit or delete
    :param time_period: time to be consider for the query
    :return: list of requests
    """
    command = [
        "/bin/bash",
        "-c",
        f"""
ex <(osc -A {api_url} request list -t {request_type} {time_period} -s accepted {project}) << EOF
# cleanup input
v/^\([0-9]\| *{request_type}:\)/d
# join lines 2 by 2
g/./j
# delete all empty lines
g/^$/d
# cleanup for submit request
%s/@.*$//g
%p
q!
EOF
[ $? -ne 0 ] && exit 0
""",
    ]
    for line in run_command_and_stream_output(command):
        line_fields = line.split()
        # ['000000', 'State:accepted', 'By:foo', 'When:2025-02-07T17:05:34', 'delete:', 'SUSE:SLFO:Main/utempter']
        # ['111111', 'State:accepted', 'By:bar', 'When:2025-02-07T17:06:21', 'submit:', 'openSUSE.org:openSUSE:Tools/product-composer@01bab0f7cdbfe17066156f2127b9da63', '->', 'SUSE:SLFO:Main']
        formated_line = f"{line_fields[3].split(':', 1)[1]} {line_fields[5].rsplit('/', 1)[1]} https://build.suse.de/request/show/{line_fields[0]}"
        print(formated_line)


def build_parser(parent_parser, config) -> None:
    """
    Builds the parser for this script. This is executed by the main CLI
    dynamically.

    :param config: Lua config table
    :return: The subparsers object from argparse.
    """
    subparser = parent_parser.add_parser(
        "requests", help="List all requests accepted or deleted in a given time."
    )
    subparser.add_argument(
        "--project",
        "-p",
        dest="project",
        help=f"OBS/IBS project (DEFAULT = {config.common.default_project}).",
        type=str,
        default=config.common.default_project,
    )
    subparser.add_argument(
        "--type",
        "-t",
        dest="request_type",
        type=str,
        choices=["submit", "delete"],
        help="Choose a request type (submit or delete).",
        required=True,
    )
    # Mutually exclusive group within the subparser
    group = subparser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--days", "-d", dest="days", help="Number of the days.", type=valid_days
    )
    group.add_argument(
        "--from_date",
        "-f",
        dest="date",
        type=valid_date,
        help="Date in YYYY-MM-DD format.",
    )
    subparser.set_defaults(func=main)


def main(args, config) -> None:
    """
    Main method that get the list of all artifacts from a given OBS project

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    time_period = ""
    if args.days:
        time_period = f"-D {args.days}"
    elif args.date:
        days = count_days(args.date)
        time_period = f"-D {days}"

    list_requests(args.osc_instance, args.project, args.request_type, time_period)
