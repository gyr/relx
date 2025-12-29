import unittest
from unittest.mock import MagicMock

from relx.providers.obs_user import OBSUserProvider


class TestOBSUserProvider(unittest.TestCase):
    """
    Unit tests for the OBSUserProvider.
    """

    def setUp(self):
        """
        Set up common mocks and the provider instance for tests.
        """
        self.mock_command_runner = MagicMock()
        self.api_url = "https://api.fake.obs"
        self.provider = OBSUserProvider(
            api_url=self.api_url,
            command_runner=self.mock_command_runner,
        )

    # --- Test cases for get_group ---
    def test_get_group_success(self):
        """
        Verifies that get_group correctly parses a successful response without full list.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<group>
  <title>Test Group</title>
  <email>test@example.com</email>
  <maintainer userid="maintainer1"/>
  <maintainer userid="maintainer2"/>
</group>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        group_info = self.provider.get_group(group="test-group")

        # Assert
        self.mock_command_runner.assert_called_once_with(
            ["osc", "-A", self.api_url, "api", "/group/test-group"]
        )
        self.assertEqual(group_info["Group"], "Test Group")
        self.assertEqual(group_info["Email"], "test@example.com")
        self.assertEqual(group_info["Maintainers"], ["maintainer1", "maintainer2"])
        self.assertNotIn("Users", group_info)  # Should not include users by default

    def test_get_group_success_full_list(self):
        """
        Verifies that get_group correctly parses a successful response with full list.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<group>
  <title>Test Group Full</title>
  <email>testfull@example.com</email>
  <maintainer userid="maint3"/>
  <person>
    <person userid="userA"/>
    <person userid="userB"/>
  </person>
  <person>
    <person userid="userC"/>
  </person>
</group>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        group_info = self.provider.get_group(group="test-group-full", is_fulllist=True)

        # Assert
        self.assertEqual(group_info["Group"], "Test Group Full")
        self.assertEqual(group_info["Maintainers"], ["maint3"])
        # Based on the original parsing logic, it will find users in nested person tags
        self.assertEqual(group_info["Users"], ["userA", "userB", "userC"])

    def test_get_group_not_found(self):
        """
        Verifies that get_group raises RuntimeError when group is not found.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Mocked command failed")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Mocked command failed"):
            self.provider.get_group(group="non-existent")

    # --- Test cases for get_user ---
    def test_get_user_by_login_success(self):
        """
        Verifies that get_user correctly parses a successful response by login.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection>
  <person>
    <login>testuser</login>
    <email>test@user.com</email>
    <realname>Test User</realname>
    <state>confirmed</state>
  </person>
</collection>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        users = list(self.provider.get_user(search_text="testuser", search_by="login"))

        # Assert
        self.mock_command_runner.assert_called_once_with(
            ["osc", "-A", self.api_url, "api", '/search/person?match=@login="testuser"']
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["User"], "testuser")
        self.assertEqual(users[0]["Email"], "test@user.com")
        self.assertEqual(users[0]["Name"], "Test User")
        self.assertEqual(users[0]["State"], "confirmed")

    def test_get_user_by_email_success(self):
        """
        Verifies that get_user correctly parses a successful response by email.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection>
  <person>
    <login>emailuser</login>
    <email>email@user.com</email>
    <realname>Email User</realname>
    <state>confirmed</state>
  </person>
</collection>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        users = list(
            self.provider.get_user(search_text="email@user.com", search_by="email")
        )

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                '/search/person?match=@email="email@user.com"',
            ]
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["User"], "emailuser")

    def test_get_user_by_realname_success(self):
        """
        Verifies that get_user correctly parses a successful response by realname.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection>
  <person>
    <login>realnameuser</login>
    <email>real@name.com</email>
    <realname>Real Name User</realname>
    <state>confirmed</state>
  </person>
</collection>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        users = list(
            self.provider.get_user(search_text="Real Name User", search_by="realname")
        )

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                '/search/person?match=contains(@realname,"Real Name User")',
            ]
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["User"], "realnameuser")

    def test_get_user_not_found(self):
        """
        Verifies that get_user returns an empty list when no user is found.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection/>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        users = list(
            self.provider.get_user(search_text="nonexistent", search_by="login")
        )

        # Assert
        self.mock_command_runner.assert_called_once()
        self.assertEqual(len(users), 0)

    def test_get_user_called_process_error(self):
        """
        Verifies that get_user raises RuntimeError on CalledProcessError.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Mocked command failed")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Mocked command failed"):
            list(self.provider.get_user(search_text="error", search_by="login"))

    def test_get_user_invalid_search_by(self):
        """
        Verifies that get_user raises ValueError for invalid search_by parameter.
        """
        # Act & Assert
        with self.assertRaisesRegex(ValueError, "Invalid search_by parameter."):
            list(self.provider.get_user(search_text="any", search_by="invalid"))

    # --- Test cases for get_entity_info ---
    def test_get_entity_info_for_user_success(self):
        """
        Verifies get_entity_info calls get_user when is_group is False.
        """
        # Arrange
        self.provider.get_user = MagicMock()
        user_data = {"User": "testuser", "Email": "test@suse.com"}
        self.provider.get_user.return_value = iter([user_data])

        # Act
        result = self.provider.get_entity_info(name="testuser", is_group=False)

        # Assert
        self.provider.get_user.assert_called_once_with(
            search_text="testuser", search_by="login"
        )
        self.assertEqual(result, user_data)

    def test_get_entity_info_for_group_success(self):
        """
        Verifies get_entity_info calls get_group when is_group is True.
        """
        # Arrange
        self.provider.get_group = MagicMock()
        group_data = {"Group": "testgroup", "Maintainers": ["user1"]}
        self.provider.get_group.return_value = group_data

        # Act
        result = self.provider.get_entity_info(name="testgroup", is_group=True)

        # Assert
        self.provider.get_group.assert_called_once_with("testgroup", is_fulllist=False)
        self.assertEqual(result, group_data)

    def test_get_entity_info_user_not_found(self):
        """
        Verifies get_entity_info raises RuntimeError if user is not found.
        """
        # Arrange
        self.provider.get_user = MagicMock()
        self.provider.get_user.return_value = iter([])  # Empty iterator

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Entity 'notfound' not found."):
            self.provider.get_entity_info(name="notfound", is_group=False)

    def test_get_entity_info_group_not_found(self):
        """
        Verifies get_entity_info raises RuntimeError if group is not found.
        """
        # Arrange
        self.provider.get_group = MagicMock(side_effect=RuntimeError("Original error"))

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Entity 'notfound' not found."):
            self.provider.get_entity_info(name="notfound", is_group=True)


if __name__ == "__main__":
    unittest.main()
