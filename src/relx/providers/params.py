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


@dataclass
class Request:
    """Represents a review request."""

    id: str
    name: str
