import re
from typing import Dict, List, Generator
from rich.progress import Progress, TaskID

from relx.utils.logger import logger_setup
from relx.utils.tools import (
    run_command,
    run_command_and_stream_output,
    running_spinner_decorator,
)

log = logger_setup(__name__)


class OBSArtifactProvider:
    """
    An artifact provider implementation for Open Build Service (OBS).
    Conforms to the ArtifactProvider protocol.
    """

    def __init__(
        self, api_url: str, invalid_start: list[str], invalid_extensions: list[str]
    ):
        self.api_url = api_url
        self.invalid_start = invalid_start
        self.invalid_extensions = invalid_extensions

    @running_spinner_decorator
    def list_packages(self, project: str) -> List[str]:
        """
        List all source packages from an OBS project.
        """
        log.debug("Listing packages for project: %s", project)
        command = f"osc -A {self.api_url} ls {project}"
        output = run_command(command.split())
        return output.stdout.split()

    def list_artifacts(
        self,
        project: str,
        packages: List[str],
        repo_info: Dict[str, str],
        progress: Progress,
        task_id: TaskID,
    ) -> Generator[str, None, None]:
        """
        List all artifacts filtered by pattern from a OBS project.
        """
        log.debug(">> pattern = %s", repo_info["pattern"])
        pattern = re.compile(repo_info["pattern"])
        log.debug(">> compiled pattern = %s", pattern)

        for package in packages:
            if re.search(pattern, package):
                command = [
                    "/bin/bash",
                    "-c",
                    f"osc -A {self.api_url} ls {project} {package} -b -r {repo_info['name']}",
                ]
                for line in run_command_and_stream_output(command):
                    line = line.strip()
                    if not line.startswith(
                        tuple(self.invalid_start)
                    ) and not line.startswith(f"{repo_info['name']}/"):
                        if not line.endswith(tuple(self.invalid_extensions)):
                            yield line
            progress.update(task_id, advance=1)
