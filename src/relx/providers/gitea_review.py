from typing import List, Any, Callable

from .base import ReviewProvider
import json

from relx.providers.params import ListRequestsParams, GiteaListRequestsParams, Request
from relx.utils.logger import logger_setup
from relx.utils.tools import run_command


log = logger_setup(__name__)


class GiteaReviewProvider(ReviewProvider):
    """
    A review provider implementation for Gitea.
    Conforms to the ReviewProvider protocol.
    """

    def __init__(
        self,
        api_url: str,
        command_runner: Callable[[List[str]], Any] = run_command,
    ):
        self.api_url = api_url
        self._run_command = command_runner

    def list_requests(self, params: ListRequestsParams) -> list[Request]:
        """
        List all requests in a 'review' state.

        :param params: An object containing the parameters for the request list.
        :return: A list of Request objects.
        """
        if not isinstance(params, GiteaListRequestsParams):
            log.error("Invalid params type for GiteaReviewProvider.list_requests")
            return []

        # Type assertion for mypy/linter, not strictly necessary for runtime
        gitea_params: GiteaListRequestsParams = params

        if not all(
            [gitea_params.reviewer, gitea_params.branch, gitea_params.repository]
        ):
            log.error("Missing reviewer, branch, or repository for Gitea list_requests")
            return []

        command_args = [
            "git",
            "obs",
            "pr",
            "list",
            "--state",
            "open",
            "--review-state",
            "REQUEST_REVIEW",
            "--no-draft",
            "--export",
            "--reviewer",
            gitea_params.reviewer,
            "--target-branch",
            gitea_params.branch,
            gitea_params.repository,
        ]

        result = self._run_command(command_args)
        if not result:
            log.info("No requests found or command returned empty output.")
            return []

        try:
            # The JSON structure is a list containing a dict, which itself contains a 'requests' list.
            data = json.loads(result)
        except json.JSONDecodeError:
            log.error(f"Failed to parse JSON from command output: {result}")
            return []

        requests = []
        if data and isinstance(data, list) and data[0] and "requests" in data[0]:
            for req_data in data[0]["requests"]:
                # Ensure 'number' and 'title' exist before accessing
                if "number" in req_data and "title" in req_data:
                    requests.append(
                        Request(id=str(req_data["number"]), name=req_data["title"])
                    )
                else:
                    log.warning(f"Skipping malformed request data: {req_data}")
        elif not data:
            log.info("No data received from Gitea command.")
        else:
            log.warning(f"Unexpected JSON structure from Gitea command: {data}")

        return requests

    def get_request_diff(self, request_id: str) -> str:
        """
        Get the diff of a specific review request.

        :param request_id: The ID of the request.
        :return: A string containing the diff.
        """
        return ""

    def approve_request(self, request_id: str, is_bugowner: bool) -> list[str]:
        """
        Approve a review request.

        :param request_id: The ID of the request to approve.
        :param is_bugowner: If True, performs the bugowner approval flow.
        :return: A list of strings representing the output of the approval commands.
        """
        return []
