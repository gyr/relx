from lxml import etree
from subprocess import CalledProcessError
from typing import Dict, List, Generator, Optional, Callable, Any

from relx.utils.logger import logger_setup
from relx.utils.tools import run_command

from .base import UserProvider

log = logger_setup(__name__)


class OBSUserProvider(UserProvider):
    """
    A user provider implementation for Open Build Service (OBS).
    Conforms to the UserProvider protocol.
    """

    def __init__(
        self,
        api_url: str,
        command_runner: Callable[[List[str]], Any] = run_command,
    ):
        self.api_url = api_url
        self._run_command = command_runner

    def get_group(
        self, group: str, is_fulllist: bool = False
    ) -> Dict[str, Optional[str] | List[Optional[str]]]:
        """
        Given a group name return the OBS info about it."

        :param group: OBS group name
        :param is_fulllist: If True, return full list of people in the group.
        :return: OBS group info
        """
        try:
            command = f"osc -A {self.api_url} api /group/{group}"
            output = self._run_command(command.split())
            tree = etree.fromstring(output.stdout.encode())
            info: Dict[str, Optional[str] | List[Optional[str]]] = {}

            title = tree.find("title")
            info["Group"] = title.text if title is not None else None

            email = tree.find("email")
            info["Email"] = email.text if email is not None else None

            maintainers = tree.findall("maintainer")
            info["Maintainers"] = [tag.get("userid") for tag in maintainers]

            if is_fulllist:
                people = tree.findall("person")
                users = []
                for person in people:
                    if person.get("userid"):
                        users.append(person.get("userid"))
                info["Users"] = users

            return info
        except CalledProcessError as e:
            log.error(f"Error fetching group {group}: {e}")
            raise RuntimeError(f"{group} not found.") from e

    def get_user(
        self,
        search_text: str,
        search_by: str,
    ) -> Generator[Dict[str, Optional[str]], None, None]:
        """
        Given a search text, return the OBS user of the bugowner"

        :param search_text: Text to be search OBS project for user info
        :param search_by: "login", "email", or "realname"
        :return: OBS user info
        """
        try:
            command_template = f"osc -A {self.api_url} api /search/person?match="
            if search_by == "login":
                command = command_template + f'@login="{search_text}"'
            elif search_by == "email":
                command = command_template + f'@email="{search_text}"'
            elif search_by == "realname":
                command = command_template + f'contains(@realname,"{search_text}")'
            else:
                raise ValueError(
                    "Invalid search_by parameter. Must be 'login', 'email', or 'realname'."
                )

            output = self._run_command(command.split())
            tree = etree.fromstring(output.stdout.encode())
            people = tree.findall("person")
            if not people:
                log.debug(
                    f"No users found for search text '{search_text}' by '{search_by}'."
                )
                return

            for person in people:
                login_tag = person.find("login")
                email_tag = person.find("email")
                realname_tag = person.find("realname")
                state_tag = person.find("state")

                info = {
                    "User": login_tag.text if login_tag is not None else None,
                    "Email": email_tag.text if email_tag is not None else None,
                    "Name": realname_tag.text if realname_tag is not None else None,
                    "State": state_tag.text if state_tag is not None else None,
                }
                yield info
        except CalledProcessError as e:
            log.error(f"Error fetching user '{search_text}' by '{search_by}': {e}")
            raise RuntimeError(f"{search_text} not found.") from e
