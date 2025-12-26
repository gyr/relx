from lxml import etree
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
        command_args = ["osc", "-A", self.api_url, "api", f"/group/{group}"]
        output = self._run_command(command_args)
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
                for user in person.findall("person"):
                    users.append(user.get("userid"))
            info["Users"] = users

        return info

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
        # Manually build the command list to ensure arguments with spaces and
        # quotes are passed correctly to the subprocess.
        command_args = ["osc", "-A", self.api_url, "api"]
        if search_by == "login":
            command_args.append(f'/search/person?match=@login="{search_text}"')
        elif search_by == "email":
            command_args.append(f'/search/person?match=@email="{search_text}"')
        elif search_by == "realname":
            command_args.append(
                f'/search/person?match=contains(@realname,"{search_text}")'
            )
        else:
            raise ValueError(
                "Invalid search_by parameter. Must be 'login', 'email', or 'realname'."
            )

        output = self._run_command(command_args)
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
