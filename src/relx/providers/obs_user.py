from lxml import etree
from typing import List, Generator, Callable, Any

from relx.utils.logger import logger_setup
from relx.utils.tools import run_command
from relx.models import OBSUser, OBSGroup

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

    def get_group(self, group: str, is_fulllist: bool = False) -> OBSGroup:
        """
        Given a group name return the OBS info about it."

        :param group: OBS group name
        :param is_fulllist: If True, return full list of people in the group.
        :return: OBS group info as an OBSGroup object.
        """
        command_args = ["osc", "-A", self.api_url, "api", f"/group/{group}"]
        output = self._run_command(command_args)
        tree = etree.fromstring(output.stdout.encode())

        title_tag = tree.find("title")
        email_tag = tree.find("email")

        maintainers = [
            userid
            for tag in tree.findall("maintainer")
            if (userid := tag.get("userid")) is not None
        ]

        users = []
        if is_fulllist:
            for person in tree.findall("person"):
                for user in person.findall("person"):
                    if user_id := user.get("userid"):
                        users.append(user_id)

        return OBSGroup(
            name=title_tag.text if title_tag is not None else None,
            email=email_tag.text if email_tag is not None else None,
            maintainers=maintainers,
            users=users,
        )

    def get_user(
        self,
        search_text: str,
        search_by: str,
    ) -> Generator[OBSUser, None, None]:
        """
        Given a search text, return the OBS user of the bugowner"

        :param search_text: Text to be search OBS project for user info
        :param search_by: "login", "email", or "realname"
        :return: A generator of OBSUser objects.
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

            yield OBSUser(
                login=login_tag.text if login_tag is not None else None,
                email=email_tag.text if email_tag is not None else None,
                realname=realname_tag.text if realname_tag is not None else None,
                state=state_tag.text if state_tag is not None else None,
            )

    def get_entity_info(self, name: str, is_group: bool) -> OBSUser | OBSGroup:
        """
        Get information about an entity, which can be a user or a group.

        :param name: The name of the user or group.
        :param is_group: True if the entity is a group, False if it's a user.
        :return: A dictionary containing the entity's information.
        """
        try:
            if is_group:
                return self.get_group(name, is_fulllist=False)
            else:
                user_iterator = self.get_user(search_text=name, search_by="login")
                return next(user_iterator)
        except (RuntimeError, StopIteration) as e:
            raise RuntimeError(f"Entity '{name}' not found.") from e
