from dataclasses import dataclass
from typing import Optional


@dataclass
class ListRequestsParams:
    """Base class for listing requests parameters."""

    pass


@dataclass
class ObsListRequestsParams(ListRequestsParams):
    """Parameters for listing OBS requests."""

    project: str
    staging: Optional[str] = None
    is_bugowner_request: bool = False


@dataclass
class GiteaListRequestsParams(ListRequestsParams):
    """Parameters for listing Gitea requests."""

    reviewer: str
    branch: str
    repository: str
    label: Optional[str] = None


@dataclass
class Request:
    """Represents a review request."""

    id: str
    name: str
    provider_type: str  # 'obs' or 'gitea'


@dataclass
class GetRequestDiffParams:
    """Base class for get request diff parameters."""

    request_id: str


@dataclass
class ObsGetRequestDiffParams(GetRequestDiffParams):
    """Parameters for getting OBS request diff."""

    pass


@dataclass
class GiteaGetRequestDiffParams(GetRequestDiffParams):
    """Parameters for getting Gitea request diff."""

    repository: str


@dataclass
class ApproveRequestParams:
    """Base class for approve request parameters."""

    request_id: str


@dataclass
class ObsApproveRequestParams(ApproveRequestParams):
    """Parameters for approving OBS requests."""

    is_bugowner: bool = False


@dataclass
class GiteaApproveRequestParams(ApproveRequestParams):
    """Parameters for approving Gitea requests."""

    repository: str
    reviewer: str
