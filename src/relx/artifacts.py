from argparse import Namespace
from rich.progress import Progress
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from relx.utils.logger import logger_setup
from relx.providers import get_artifact_provider


log = logger_setup(__name__)


def build_parser(parent_parser, config: Dict[str, Any]) -> None:
    """
    Builds the parser for this script. This is executed by the main CLI
    dynamically.

    :param config: Lua config table
    :return: The subparsers object from argparse.
    """
    subparser = parent_parser.add_parser(
        "artifacts", help="Return the list of artifacts from a OBS project."
    )
    subparser.add_argument(
        "--project",
        "-p",
        dest="project",
        help=f"OBS/IBS project (DEFAULT = {config['default_product']}).",
        type=str,
        default=config["default_product"],
    )
    subparser.set_defaults(func=main)


def main(args: Namespace, config: Dict[str, Any]) -> None:
    """
    Main method that get the list of all artifacts from a given OBS project
    in parallel.

    :param args: Argparse Namespace that has all the arguments
    :param config: Lua config table
    """
    provider = get_artifact_provider(
        provider_name="obs", api_url=args.osc_instance, config=config
    )

    packages = provider.list_packages(project=args.project)

    total_steps = len(config["artifacts"]["repo_info"]) * len(packages)
    with Progress() as progress:
        task_id = progress.add_task("Searching artifacts", total=total_steps)

        def on_package_done():
            """Callback to advance the progress bar from any thread."""
            progress.update(task_id, advance=1)

        with ThreadPoolExecutor(max_workers=10) as executor:
            # A wrapper function to call the provider and collect results
            def fetch_artifacts(repo_info):
                return list(
                    provider.list_artifacts(
                        project=args.project,
                        packages=packages,
                        repo_info=repo_info,
                        progress_callback=on_package_done,
                    )
                )

            # Submit all tasks to the executor
            future_to_repo = {
                executor.submit(fetch_artifacts, repo): repo
                for repo in config["artifacts"]["repo_info"]
            }

            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]["name"]
                try:
                    artifacts = future.result()
                    # Print the collected artifacts for the completed repo
                    for artifact in sorted(artifacts):
                        print(artifact)
                except Exception as exc:
                    log.error("%r generated an exception: %s", repo_name, exc)
