from lxml import etree
from typing import List, Any, Callable, Optional

from .base import ReviewProvider
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

    def list_requests(
        self,
        project: str,
        staging: Optional[str] = None,
        is_bugowner_request: bool = False,
    ) -> list[tuple[str, str]]:
        """
        List all requests in a 'review' state.

        :param project: The project to search in.
        :param staging: The optional staging project letter.
        :param is_bugowner_request: If True, searches for bugowner requests.
        :return: A list of (request_id, package_name) tuples.
        """
        command_args = ["osc", "-A", self.api_url, "api"]
        if is_bugowner_request:
            command_args.append(
                f"/search/request?match=state/@name='review' and action/@type='set_bugowner' and action/target/@project='{project}'&withhistory=0&withfullhistory=0"
            )
        elif staging:
            project = f"{project}:Staging:{staging}"
            command_args.append(
                f"/search/request?match=state/@name='review' and review/@state='new' and review/@by_project='{project}'&withhistory=0&withfullhistory=0"
            )
        else:
            command_args.append(
                f"/search/request?match=state/@name='review' and review/@state='new' and target/@project='{project}'&withhistory=0&withfullhistory=0"
            )
        result = self._run_command(command_args)

        tree = etree.fromstring(result.stdout.encode())

        requests = []

        for request in tree.findall("request"):
            state_tag = request.find("state")
            if state_tag is not None and state_tag.get("name") == "review":
                relmgr_review = request.find("review[@by_group='sle-release-managers']")
                if relmgr_review is not None and relmgr_review.get("state") == "new":
                    request_id = request.get("id")
                    target_action = request.find("action/target")
                    package_name = None
                    if target_action is not None:
                        package_name = target_action.get("package")

                    if request_id is not None and package_name is not None:
                        request_tuple = (request_id, package_name)
                        log.debug(f"{request_tuple=}")
                        requests.append(request_tuple)
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
