import unittest
from unittest.mock import MagicMock

from relx.providers.obs import OBSArtifactProvider


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

    def test_list_artifacts_filtering_and_command(self):
        """
        Verifies that list_artifacts correctly filters results and calls the stream runner.
        """
        # Arrange
        # Mock the progress bar objects, as they are passed directly
        mock_progress = MagicMock()
        mock_task_id = MagicMock()

        # Simulate the streamed output from the command runner
        self.mock_stream_runner.return_value = iter(
            [
                "artifact-1.rpm",
                "repo/should_be_filtered.txt",
                "artifact-2.iso",
                "artifact-3.sig",  # Should be filtered by extension
                "artifact-4.qcow2",
                "artifact-5.meta",  # Should be filtered by extension
            ]
        )

        packages_to_check = ["package-a"]
        repo_info = {"name": "repo", "pattern": ".*"}

        # Act
        # The method returns a generator, so we consume it into a list
        artifacts = list(
            self.provider.list_artifacts(
                project="fake:project",
                packages=packages_to_check,
                repo_info=repo_info,
                progress=mock_progress,
                task_id=mock_task_id,
            )
        )

        # Assert
        # 1. Check that the correct command was executed
        expected_command = [
            "/bin/bash",
            "-c",
            "osc -A https://api.fake.obs ls fake:project package-a -b -r repo",
        ]
        self.mock_stream_runner.assert_called_once_with(expected_command)

        # 2. Check that the output was filtered correctly
        self.assertEqual(
            artifacts, ["artifact-1.rpm", "artifact-2.iso", "artifact-4.qcow2"]
        )

        # 3. Verify the progress bar was updated
        mock_progress.update.assert_called_once_with(mock_task_id, advance=1)


if __name__ == "__main__":
    unittest.main()
