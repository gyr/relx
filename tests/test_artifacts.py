import unittest
from unittest.mock import patch, MagicMock, ANY
from argparse import Namespace
import io
from contextlib import redirect_stdout

from relx.artifacts import main as artifacts_main


class TestArtifactsSubcommand(unittest.TestCase):
    """
    Tests the artifacts subcommand's main logic.
    """

    @patch("relx.artifacts.Progress")
    @patch("relx.artifacts.get_artifact_provider")
    def test_main_flow_and_output(self, mock_get_provider, mock_rich_progress):
        """
        Verifies the main flow: provider creation, method calls, and final output.
        """
        # --- Arrange ---
        # 1. Mock the provider and its methods' return values
        mock_provider = MagicMock()
        mock_provider.list_packages.return_value = ["package1", "package2"]
        # The list_artifacts method should return a generator
        mock_provider.list_artifacts.return_value = iter(
            ["artifact1.iso", "artifact2.qcow2"]
        )
        mock_get_provider.return_value = mock_provider

        # 2. Prepare arguments and config objects similar to the main CLI
        args = Namespace(osc_instance="fake_api_url", project="fake_project")
        config = {
            "default_product": "fake_project",
            "artifacts": {
                "repo_info": [{"name": "repo1", "pattern": ".*"}],
            },
        }

        # --- Act ---
        # 3. Capture stdout to check the printed output
        string_io = io.StringIO()
        with redirect_stdout(string_io):
            artifacts_main(args, config)
        output = string_io.getvalue()

        # --- Assert ---
        # 4. Verify the provider factory was called correctly
        mock_get_provider.assert_called_once_with(
            provider_name="obs", api_url="fake_api_url", config=config
        )

        # 5. Verify the provider's methods were called with the correct arguments
        mock_provider.list_packages.assert_called_once_with(project="fake_project")
        mock_provider.list_artifacts.assert_called_once_with(
            project="fake_project",
            packages=["package1", "package2"],
            repo_info={"name": "repo1", "pattern": ".*"},
            progress_callback=ANY,  # We check that a callback was passed
        )

        # 6. Verify the final output was printed correctly
        expected_output = "artifact1.iso\nartifact2.qcow2\n"
        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()
