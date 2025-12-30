from lxml import etree
from typing import List, Any, Callable

from .base import ReviewProvider
from relx.providers.params import ListRequestsParams, ObsListRequestsParams, Request
from relx.utils.logger import logger_setup
from relx.utils.tools import run_command


log = logger_setup(__name__)


class OBSReviewProvider(ReviewProvider):
    """
    A review provider implementation for Open Build Service (OBS).
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
        if not isinstance(params, ObsListRequestsParams):
            log.error("Invalid params type for OBSReviewProvider.list_requests")
            return []

        obs_params: ObsListRequestsParams = params

        command_args = ["osc", "-A", self.api_url, "api"]
        project = obs_params.project
        if obs_params.is_bugowner_request:
            command_args.append(
                f"/search/request?match=state/@name='review' and action/@type='set_bugowner' and action/target/@project='{project}'&withhistory=0&withfullhistory=0"
            )
        elif obs_params.staging:
            staged_project = f"{project}:Staging:{obs_params.staging}"
            command_args.append(
                f"/search/request?match=state/@name='review' and review/@state='new' and review/@by_project='{staged_project}'&withhistory=0&withfullhistory=0"
            )
        else:
            command_args.append(
                f"/search/request?match=state/@name='review' and review/@state='new' and target/@project='{project}'&withhistory=0&withfullhistory=0"
            )
        result = self._run_command(command_args)

        # Handle empty result
        if not result or not result.stdout:
            log.info("No requests found or command returned empty output.")
            return []

        tree = etree.fromstring(result.stdout.encode())

        requests = []

        for request_element in tree.findall(
            "request"
        ):  # Renamed 'request' to 'request_element' to avoid conflict with Request dataclass
            state_tag = request_element.find("state")
            if state_tag is not None and state_tag.get("name") == "review":
                relmgr_review = request_element.find(
                    "review[@by_group='sle-release-managers']"
                )
                if relmgr_review is not None and relmgr_review.get("state") == "new":
                    request_id = request_element.get("id")
                    target_action = request_element.find("action/target")
                    package_name = None
                    if target_action is not None:
                        package_name = target_action.get("package")

                    if request_id is not None and package_name is not None:
                        request_obj = Request(
                            id=request_id, name=package_name, provider_type="obs"
                        )
                        log.debug(f"{request_obj=}")
                        requests.append(request_obj)
        return requests

    def get_request_diff(self, request_id: str) -> str:
        """
        Get the diff of a specific review request.

        :param request_id: The ID of the request.
        :return: A string containing the diff.
        """
        command = f"osc -A {self.api_url} review show -d {request_id}"
        output = self._run_command(command.split())
        return output.stdout

    def approve_request(self, request_id: str, is_bugowner: bool) -> list[str]:
        """
        Approve a review request.

        :param request_id: The ID of the request to approve.
        :param is_bugowner: If True, performs the bugowner approval flow.
        :return: A list of strings representing the output of the approval commands.
        """
        groups: list = ["sle-release-managers"]
        lines = []
        if is_bugowner:
            groups.append("sle-staging-managers")
        for group in groups:
            command_args = [
                "osc",
                "-A",
                self.api_url,
                "review",
                "accept",
                "-m",
                "OK",  # Pass "OK" directly as an argument
                "-G",
                group,
                request_id,
            ]
            output = self._run_command(command_args)
            lines.append(f"{group}: {output.stdout}")
        return lines
