"""
This module defines the base protocol for all provider implementations.
"""

from typing import Dict, List, Generator, Protocol, Optional, Callable

from relx.providers.params import (
    ListRequestsParams,
    Request,
    GetRequestDiffParams,
    ApproveRequestParams,
)


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

    def get_entity_info(self, name: str, is_group: bool) -> dict:
        """
        Get information about an entity, which can be a user or a group.

        :param name: The name of the user or group.
        :param is_group: True if the entity is a group, False if it's a user.
        :return: A dictionary containing the entity's information.
        """
        ...


class PackageProvider(Protocol):
    """
    A protocol that defines the interface for a package information provider.
    """

    def is_shipped(self, package: str, productcomposer: str) -> bool:
        """
        Checks if a package is shipped in a given product.

        :param package: The package name.
        :param productcomposer: The product composer project.
        :return: True if the package is shipped, False otherwise.
        """
        ...

    def get_source_package(self, project: str, package: str) -> str:
        """
        Get the source package from OBS for a given binary package.

        :param project: The OBS project.
        :param package: The binary package name.
        :return: The source package name.
        """
        ...

    def get_bugowner(self, package: str) -> tuple[list, bool]:
        """
        Get the bugowner for a given package.

        :param package: The package name.
        :return: A tuple containing a list of bugowners and a boolean indicating if it's a group.
        """
        ...


class ReviewProvider(Protocol):
    """
    A protocol that defines the interface for a code review provider.
    """

    def __init__(self, api_url: str):
        """
        Initializes the ReviewProvider.

        :param api_url: The API URL for the provider.
        """
        ...

    def list_requests(self, params: ListRequestsParams) -> list[Request]:
        """
        List all requests in a 'review' state.

        :param params: An object containing the parameters for the request list.
        :return: A list of (request_id, package_name) tuples.
        """
        ...

    def get_request_diff(self, params: GetRequestDiffParams) -> str:
        """
        Get the diff of a specific review request.

        :param request_id: The ID of the request.
        :return: A string containing the diff.
        """
        ...

    def approve_request(self, params: ApproveRequestParams) -> list[str]:
        """
        Approve a review request.

        :param request_id: The ID of the request to approve.
        :param is_bugowner: If True, performs the bugowner approval flow.
        :return: A list of strings representing the output of the approval commands.
        """
        ...
