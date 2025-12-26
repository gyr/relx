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


class UserProvider(Protocol):
    """
    A protocol that defines the interface for a user provider.
    """

    def get_user(
        self, search_text: str, search_by: str
    ) -> Generator[Dict[str, Optional[str]], None, None]:
        """
        Given a search text, return the OBS user of the bugowner

        :param search_text: Text to be search OBS project for user info
        :param search_by: "login", "email", or "realname"
        :return: OBS user info
        """
        ...

    def get_group(
        self, group: str, is_fulllist: bool = False
    ) -> Dict[str, Optional[str] | List[Optional[str]]]:
        """
        Given a group name return the OBS info about it."

        :param group: OBS group name
        :param is_fulllist: If True, return full list of people in the group.
        :return: OBS group info
        """
        ...
