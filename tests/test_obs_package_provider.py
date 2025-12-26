import unittest
from unittest.mock import MagicMock
from subprocess import CalledProcessError

from relx.providers.obs_package import OBSPackageProvider


class TestOBSPackageProvider(unittest.TestCase):
    """
    Unit tests for the OBSPackageProvider.
    """

    def setUp(self):
        """
        Set up common mocks and the provider instance for tests.
        """
        self.mock_command_runner = MagicMock()
        self.mock_stream_runner = MagicMock()
        self.api_url = "https://api.fake.obs"
        self.provider = OBSPackageProvider(
            api_url=self.api_url,
            command_runner=self.mock_command_runner,
            stream_runner=self.mock_stream_runner,
        )

    # --- Test cases for is_shipped ---
    def test_is_shipped_true(self):
        """
        Verifies is_shipped returns True when the package is found.
        """
        # Arrange
        self.mock_stream_runner.return_value = iter(
            ["some line with package-name other text"]
        )

        # Act
        result = self.provider.is_shipped(
            package="package-name", productcomposer="fake-product"
        )

        # Assert
        self.mock_stream_runner.assert_called_once_with(
            ["/bin/bash", "-c", f"osc -A {self.api_url} cat fake-product"]
        )
        self.assertTrue(result)

    def test_is_shipped_false(self):
        """
        Verifies is_shipped returns False when the package is not found.
        """
        # Arrange
        self.mock_stream_runner.return_value = iter(
            ["some line without the package", "another line"]
        )

        # Act
        result = self.provider.is_shipped(
            package="package-name", productcomposer="fake-product"
        )

        # Assert
        self.mock_stream_runner.assert_called_once()
        self.assertFalse(result)

        # --- Test cases for get_source_package ---
        def test_get_source_package_success(self):
            """
            Verifies get_source_package successfully parses the source package name.
            """
            # Arrange
            mock_output = MagicMock()
            # The format is <project> <source>:<subpackage-or-whatever>
            # The code should extract <source>.
            mock_output.stdout = "fake-project my-source-package:some-other-info"
            self.mock_command_runner.return_value = mock_output

            # Act
            source_package = self.provider.get_source_package(
                project="fake-project", package="binary-package"
            )

            # Assert
            self.mock_command_runner.assert_called_once_with(
                ["osc", "-A", self.api_url, "bse", "binary-package"]
            )
            # It should get the part before the first colon.
            self.assertEqual(source_package, "my-source-package")

    def test_get_source_package_not_found(self):
        """
        Verifies get_source_package raises RuntimeError if no source is found.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "some other output"
        self.mock_command_runner.return_value = mock_output

        # Act & Assert
        with self.assertRaisesRegex(
            RuntimeError, "No source package found for binary-package in fake-project."
        ):
            self.provider.get_source_package(
                project="fake-project", package="binary-package"
            )

    # --- Test cases for get_bugowner ---
    def test_get_bugowner_person_success(self):
        """
        Verifies get_bugowner successfully parses a person as bugowner.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<owners>
  <owner>
    <person name="testuser" />
  </owner>
</owners>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        bugowners, is_group = self.provider.get_bugowner(package="source-package")

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                "/search/owner?package=source-package&filter=bugowner",
            ]
        )
        self.assertEqual(bugowners, ["testuser"])
        self.assertFalse(is_group)

    def test_get_bugowner_group_success(self):
        """
        Verifies get_bugowner successfully parses a group as bugowner.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<owners>
  <owner>
    <group name="test-group" />
  </owner>
</owners>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        bugowners, is_group = self.provider.get_bugowner(package="source-package")

        # Assert
        self.mock_command_runner.assert_called_once()
        self.assertEqual(bugowners, ["test-group"])
        self.assertTrue(is_group)

    def test_get_bugowner_not_found(self):
        """
        Verifies get_bugowner returns empty list if no owner is found.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "<owners/>"
        self.mock_command_runner.return_value = mock_output

        # Act
        bugowners, is_group = self.provider.get_bugowner(package="source-package")

        # Assert
        self.mock_command_runner.assert_called_once()
        self.assertEqual(bugowners, [])
        self.assertFalse(is_group)

    def test_get_bugowner_plusplus_package(self):
        """
        Verifies get_bugowner correctly escapes '++' in package names.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "<owners/>"
        self.mock_command_runner.return_value = mock_output

        # Act
        self.provider.get_bugowner(package="package++name")

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                "/search/owner?package=package%2B%2Bname&filter=bugowner",
            ]
        )

    def test_get_bugowner_error(self):
        """
        Verifies get_bugowner raises RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = CalledProcessError(1, "cmd")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "source-package has no bugowner"):
            self.provider.get_bugowner(package="source-package")


if __name__ == "__main__":
    unittest.main()
