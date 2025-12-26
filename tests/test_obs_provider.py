import unittest
from unittest.mock import MagicMock, call

from relx.providers.obs_artifact import OBSArtifactProvider


class TestOBSArtifactProvider(unittest.TestCase):
    """
    Unit tests for the OBSArtifactProvider.
    """

    def setUp(self):
        """
        Set up common mocks and the provider instance for tests.
        """
        self.mock_command_runner = MagicMock()
        self.mock_stream_runner = MagicMock()
        self.provider = OBSArtifactProvider(
            api_url="https://api.fake.obs",
            invalid_start=["repo/"],
            invalid_extensions=[".meta", ".sig"],
            command_runner=self.mock_command_runner,
            stream_runner=self.mock_stream_runner,
        )

    def test_list_packages(self):
        """
        Verifies that list_packages constructs the correct command and returns a parsed list.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "package-a\npackage-b\npackage-c"
        self.mock_command_runner.return_value = mock_output

        # Act
        packages = self.provider.list_packages(project="fake:project")

        # Assert
        self.mock_command_runner.assert_called_once_with(
            ["osc", "-A", "https://api.fake.obs", "ls", "fake:project"]
        )
        self.assertEqual(packages, ["package-a", "package-b", "package-c"])

    def test_list_artifacts_filtering_and_callback(self):
        """
        Verifies that list_artifacts correctly filters results and calls the callback.
        """
        # Arrange
        mock_progress_callback = MagicMock()

        # Each call to the stream runner should return a new iterator.
        # Using side_effect is the correct way to mock this.
        self.mock_stream_runner.side_effect = [
            iter(
                [
                    "artifact-1.rpm",
                    "repo/should_be_filtered.txt",
                ]
            ),
            iter(
                [
                    "artifact-2.iso",
                    "artifact-3.sig",  # Should be filtered
                ]
            ),
        ]

        packages_to_check = ["package-a", "package-b"]
        repo_info = {"name": "repo", "pattern": ".*"}

        # Act
        artifacts = list(
            self.provider.list_artifacts(
                project="fake:project",
                packages=packages_to_check,
                repo_info=repo_info,
                progress_callback=mock_progress_callback,
            )
        )

        # Assert
        # 1. Check that the command was executed for each package that matches the pattern
        expected_calls = [
            call(
                [
                    "/bin/bash",
                    "-c",
                    "osc -A https://api.fake.obs ls fake:project package-a -b -r repo",
                ]
            ),
            call(
                [
                    "/bin/bash",
                    "-c",
                    "osc -A https://api.fake.obs ls fake:project package-b -b -r repo",
                ]
            ),
        ]
        self.mock_stream_runner.assert_has_calls(expected_calls)

        # 2. Check that the output was filtered correctly
        self.assertEqual(artifacts, ["artifact-1.rpm", "artifact-2.iso"])

        # 3. Verify the progress callback was called for each package
        self.assertEqual(mock_progress_callback.call_count, len(packages_to_check))


if __name__ == "__main__":
    unittest.main()
