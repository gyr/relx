from typing import List, Any, Callable

from .base import ReviewProvider
import json

from relx.providers.params import (
    ListRequestsParams,
    GiteaListRequestsParams,
    Request,
    GetRequestDiffParams,
    GiteaGetRequestDiffParams,
    ApproveRequestParams,
    GiteaApproveRequestParams,
)
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
        if not result or not result.stdout:
            log.info("No requests found or command returned empty output.")
            return []

        try:
            # The JSON structure is a list containing a dict, which itself contains a 'requests' list.
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            log.error(f"Failed to parse JSON from command output: {result.stdout}")
            return []

        requests = []
        if data and isinstance(data, list) and data[0] and "requests" in data[0]:
            for req_data in data[0]["requests"]:
                # Ensure 'number' and 'title' exist before accessing
                if "number" in req_data and "title" in req_data:
                    requests.append(
                        Request(
                            id=str(req_data["number"]),
                            name=req_data["title"],
                            provider_type="gitea",
                        )
                    )
                else:
                    log.warning(f"Skipping malformed request data: {req_data}")
        elif not data:
            log.info("No data received from Gitea command.")
        else:
            log.warning(f"Unexpected JSON structure from Gitea command: {data}")

        return requests

    def get_request_diff(self, params: GetRequestDiffParams) -> str:
        """
        Get the diff of a specific review request.

        :param params: An object containing the parameters for the request diff.
        :return: A string containing the diff.
        """
        if not isinstance(params, GiteaGetRequestDiffParams):
            log.error("Invalid params type for GiteaReviewProvider.get_request_diff")
            return ""

        command_args = [
            "git",
            "obs",
            "pr",
            "show",
            "--timeline",
            "--patch",
            f"{params.repository}#{params.request_id}",
        ]
        result = self._run_command(command_args)
        if not result or not result.stdout:
            log.info(
                f"No diff found for PR {params.request_id} in {params.repository} or command returned empty output."
            )
            return ""
        return result.stdout

    def approve_request(self, params: ApproveRequestParams) -> list[str]:
        """
        Approve a review request.

        :param params: An object containing the parameters for the approval.
        :return: A list of strings representing the output of the approval commands.
        """
        if not isinstance(params, GiteaApproveRequestParams):
            log.error("Invalid params type for GiteaReviewProvider.approve_request")
            return []

        command_args = [
            "git",
            "obs",
            "pr",
            "comment",
            f"{params.repository}#{params.request_id}",
            "-m",
            f"@{params.reviewer}: approve",  # Corrected: removed leading space
        ]
        result = self._run_command(command_args)
        if not result:
            log.info(
                f"No output from approve comment for PR {params.request_id} in {params.repository}."
            )
            return []
        return [result.stdout]
