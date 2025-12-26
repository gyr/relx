import unittest
from unittest.mock import MagicMock, patch, call
from argparse import Namespace

from relx import users
from relx.providers import base
from relx.exceptions import RelxResourceNotFoundError


class TestUsersCLI(unittest.TestCase):
    """
    Unit tests for the relx users CLI subcommand.
    """

    def setUp(self):
        """
        Set up common mocks and objects for tests.
        """
        self.mock_user_provider = MagicMock(spec=base.UserProvider)
        self.mock_config = {"osc_instance": "https://api.fake.obs"}
        self.mock_args = Namespace(
            osc_instance="https://api.fake.obs",
            osc_config="mock_config_path",
            debug=False,
            group=False,
            login=False,
            email=False,
            name=False,
            search_text="",
            func=users.main,
        )

    @patch("relx.users.Rule")
    @patch("relx.users.Table")
    @patch("relx.users.Console")
    @patch("relx.users.get_user_provider")
    def test_main_group_success(
        self,
        mock_get_user_provider,
        mock_console_class,
        mock_table_class,
        mock_rule_class,
    ):
        """
        Test 'relx users --group <group-name>' command for successful group info.
        """
        # Arrange
        self.mock_args.group = True
        self.mock_args.search_text = "test-group"
        mock_console_instance = mock_console_class.return_value
        mock_table_instance = mock_table_class.return_value

        expected_group_info = {
            "Group": "test-group",
            "Email": "group@example.com",
            "Maintainers": ["maint1", "maint2"],
            "Users": ["userA", "userB"],
        }
        self.mock_user_provider.get_group.return_value = expected_group_info
        mock_get_user_provider.return_value = self.mock_user_provider

        # Act
        users.main(self.mock_args, self.mock_config)

        # Assert
        self.mock_user_provider.get_group.assert_called_once_with(
            group="test-group", is_fulllist=True
        )

        expected_calls = [
            call("Group", "test-group"),
            call("Email", "group@example.com"),
            call("Maintainers", "['maint1', 'maint2']"),
            call("Users", "['userA', 'userB']"),
        ]
        mock_table_instance.add_row.assert_has_calls(expected_calls, any_order=True)

        mock_console_instance.print.assert_called_once_with(mock_table_instance)

    @patch("relx.users.get_user_provider")
    def test_main_group_not_found(self, mock_get_user_provider):
        """
        Test 'relx users --group <non-existent>' command for group not found.
        """
        # Arrange
        self.mock_args.group = True
        self.mock_args.search_text = "non-existent-group"
        self.mock_user_provider.get_group.return_value = {}  # Empty dict for not found
        mock_get_user_provider.return_value = self.mock_user_provider

        # Act & Assert
        with self.assertRaisesRegex(
            RelxResourceNotFoundError, "Group 'non-existent-group' not found."
        ):
            users.main(self.mock_args, self.mock_config)

    @patch("relx.users.Rule")
    @patch("relx.users.Table")
    @patch("relx.users.Console")
    @patch("relx.users.get_user_provider")
    def test_main_user_login_success(
        self,
        mock_get_user_provider,
        mock_console_class,
        mock_table_class,
        mock_rule_class,
    ):
        """
        Test 'relx users --login <user-login>' command for successful user info.
        """
        # Arrange
        self.mock_args.login = True
        self.mock_args.search_text = "testuser"
        mock_console_instance = mock_console_class.return_value
        mock_table_instance = mock_table_class.return_value

        expected_user_info = [
            {
                "User": "testuser",
                "Email": "user@example.com",
                "Name": "Test User",
                "State": "confirmed",
            }
        ]
        self.mock_user_provider.get_user.return_value = iter(expected_user_info)
        mock_get_user_provider.return_value = self.mock_user_provider

        # Act
        users.main(self.mock_args, self.mock_config)

        # Assert
        self.mock_user_provider.get_user.assert_called_once_with(
            search_text="testuser", search_by="login"
        )

        expected_calls = [
            call("User", "testuser"),
            call("Email", "user@example.com"),
            call("Name", "Test User"),
            call("State", "confirmed"),
            call(mock_rule_class.return_value, mock_rule_class.return_value),
        ]
        mock_table_instance.add_row.assert_has_calls(expected_calls)
        mock_console_instance.print.assert_called_once_with(mock_table_instance)

    @patch("relx.users.get_user_provider")
    def test_main_user_not_found(self, mock_get_user_provider):
        """
        Test 'relx users --login <non-existent>' command for user not found.
        """
        # Arrange
        self.mock_args.login = True
        self.mock_args.search_text = "nonexistent"
        self.mock_user_provider.get_user.return_value = iter([])  # Empty generator
        mock_get_user_provider.return_value = self.mock_user_provider

        # Act & Assert
        with self.assertRaisesRegex(
            RelxResourceNotFoundError, "User 'nonexistent' not found."
        ):
            users.main(self.mock_args, self.mock_config)

    @patch("relx.users.get_user_provider")
    def test_main_user_invalid_search_by(self, mock_get_user_provider):
        """
        Test main handling of ValueError from provider.
        """
        # Arrange
        self.mock_args.login = False
        self.mock_args.name = True  # Using a different search to ensure the logic works
        self.mock_args.search_text = "anyuser"
        self.mock_user_provider.get_user.side_effect = ValueError(
            "Invalid search_by parameter."
        )
        mock_get_user_provider.return_value = self.mock_user_provider

        # Act & Assert
        with self.assertRaises(ValueError):
            users.main(self.mock_args, self.mock_config)
