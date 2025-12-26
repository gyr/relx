import re
from lxml import etree
from subprocess import CalledProcessError
from typing import List, Any, Callable

from .base import PackageProvider
from relx.utils.logger import logger_setup
from relx.utils.tools import (
    run_command,
    run_command_and_stream_output,
)

log = logger_setup(__name__)


class OBSPackageProvider(PackageProvider):
    """
    An package provider implementation for Open Build Service (OBS).
    Conforms to the PackageProvider protocol.
    """

    def __init__(
        self,
        api_url: str,
        command_runner: Callable[[List[str]], Any] = run_command,
        stream_runner: Callable[[List[str]], Any] = run_command_and_stream_output,
    ):
        self.api_url = api_url
        self._run_command = command_runner
        self._stream_runner = stream_runner

    def is_shipped(self, package: str, productcomposer: str) -> bool:
        command = [
            "/bin/bash",
            "-c",
            f"osc -A {self.api_url} cat {productcomposer}",
        ]
        pattern = r"\b" + re.escape(package) + r"\b"
        for line in self._stream_runner(command):
            if re.search(pattern, line):
                log.debug(line)
                return True
        return False

    def get_source_package(self, project: str, package: str) -> str:
        """
        Get the source package from OBS.

        :param project: OBS project
        :param package: binary name
        :return: source package
        """
        command = f"osc -A {self.api_url} bse {package}"
        output = self._run_command(command.split())
        filtered_output = [
            line
            for line in output.stdout.splitlines()
            if line.startswith(f"{project} ")
        ]
        if len(filtered_output) == 0:
            raise RuntimeError(f"No source package found for {package} in {project}.")
        packages = []
        for line in filtered_output:
            items = line.split()
            item = items[1].split(":")
            if len(item) > 0:
                packages.append(item[0])
        source_package = set(packages)
        if len(source_package) != 1:
            log.debug(
                "More than 1 source package found for %s in %s: %s",
                package,
                project,
                source_package,
            )
        return str(next(iter(source_package)))

    def get_bugowner(self, package: str) -> tuple[list, bool]:
        """
        Given a source package return the OBS user of the bugowner"

        :param package: binary name
        :return: source package
        """
        fixed_package = package.replace("++", "%2B%2B")
        command_args = [
            "osc",
            "-A",
            self.api_url,
            "api",
            f"/search/owner?package={fixed_package}&filter=bugowner",
        ]
        bugowners = []
        is_group = False
        try:
            output = self._run_command(command_args)
            tree = etree.fromstring(output.stdout.encode())
            people = tree.findall("owner/person")
            if len(people) != 0:
                bugowners = [person.get("name") for person in people]
                return bugowners, is_group

            groups = tree.findall("owner/group")
            if len(groups) != 0:
                is_group = True
                bugowners = [group.get("name") for group in groups]
                return bugowners, is_group

            log.debug("No bugowner found for %s.", package)
            return bugowners, is_group
        except CalledProcessError as e:
            raise RuntimeError(f"{package} has no bugowner") from e
