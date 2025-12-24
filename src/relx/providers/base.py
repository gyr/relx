"""
This module defines the base protocol for all provider implementations.
"""

from typing import Dict, List, Generator, Protocol
from rich.progress import Progress, TaskID


class ArtifactProvider(Protocol):
    """
    A protocol that defines the interface for an artifact provider.
    """

    def list_packages(self, project: str) -> List[str]:
        """
        List all source packages from a project.

        :param project: The project identifier.
        :return: A list of source package names.
        """
        ...

    def list_artifacts(
        self,
        project: str,
        packages: List[str],
        repo_info: Dict[str, str],
        progress: Progress,
        task_id: TaskID,
    ) -> Generator[str, None, None]:
        """
        List all artifacts for the given packages and repository info.

        :param project: The project identifier.
        :param packages: A list of source packages to inspect.
        :param repo_info: A dictionary with repository-specific information.
        :param progress: A rich.progress.Progress instance for UI feedback.
        :param task_id: A rich.progress.TaskID for updating the progress bar.
        :return: A generator that yields artifact strings.
        """
        ...
