"""
This module defines the base protocol for all provider implementations.
"""

from typing import Dict, List, Generator, Protocol, Optional, Callable


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
        progress_callback: Optional[Callable[[], None]] = None,
    ) -> Generator[str, None, None]:
        """
        List all artifacts for the given packages and repository info.

        :param project: The project identifier.
        :param packages: A list of source packages to inspect.
        :param repo_info: A dictionary with repository-specific information.
        :param progress_callback: An optional callback to signal progress.
        :return: A generator that yields artifact strings.
        """
        ...
