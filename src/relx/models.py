from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OBSUser:
    """Represents an OBS user."""

    login: Optional[str]
    email: Optional[str]
    realname: Optional[str]
    state: Optional[str]


@dataclass
class OBSGroup:
    """Represents an OBS group."""

    name: Optional[str]
    email: Optional[str]
    maintainers: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
