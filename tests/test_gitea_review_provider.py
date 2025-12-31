import unittest
import json
from unittest.mock import MagicMock
from argparse import Namespace

from relx.providers.gitea_review import GiteaReviewProvider
from relx.providers.params import (
    GiteaListRequestsParams,
    GiteaGetRequestDiffParams,
    GiteaApproveRequestParams,
    Request,
)


class TestGiteaReviewProvider(unittest.TestCase):
    """
    Unit tests for the GiteaReviewProvider.
    """

    def setUp(self):
        """
        Set up common mocks and the provider instance for tests.
        """
        self.mock_command_runner = MagicMock()
        # api_url is required by the constructor but not used by Gitea provider methods
        self.api_url = "https://gitea.fake"
        self.provider = GiteaReviewProvider(
            api_url=self.api_url,
            command_runner=self.mock_command_runner,
        )

    # --- Test cases for list_requests ---
    def test_list_requests_success(self):
        """
        Verifies list_requests correctly parses valid JSON output.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = json.dumps(
            [
                {
                    "requests": [
                        {"number": 101, "title": "Feat: New feature"},
                        {"number": 102, "title": "Fix: A bug"},
                    ]
                }
            ]
        )
        self.mock_command_runner.return_value = mock_output
        params = GiteaListRequestsParams(
            repository="my-repo", branch="main", reviewer="me"
        )

        # Act
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "git",
                "obs",
                "pr",
                "list",
                "--state",
                "open",
                "--review-state",
                "REQUEST_REVIEW",
                "--no-draft",
                "--export",
                "--reviewer",
                "me",
                "--target-branch",
                "main",
                "my-repo",
            ]
        )
        self.assertEqual(
            requests,
            [
                Request(id="101", name="Feat: New feature", provider_type="gitea"),
                Request(id="102", name="Fix: A bug", provider_type="gitea"),
            ],
        )

    def test_list_requests_no_reviews(self):
        """
        Verifies list_requests returns an empty list when no reviews are found.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = json.dumps([{"requests": []}])
        self.mock_command_runner.return_value = mock_output
        params = GiteaListRequestsParams(
            repository="my-repo", branch="main", reviewer="me"
        )

        # Act
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once()
        self.assertEqual(requests, [])

    def test_list_requests_invalid_json(self):
        """
        Verifies list_requests returns an empty list on malformed JSON.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "this is not json"
        self.mock_command_runner.return_value = mock_output
        params = GiteaListRequestsParams(
            repository="my-repo", branch="main", reviewer="me"
        )

        # Act
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once()
        self.assertEqual(requests, [])

    def test_list_requests_command_error(self):
        """
        Verifies list_requests propagates RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Command failed")
        params = GiteaListRequestsParams(
            repository="my-repo", branch="main", reviewer="me"
        )

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Command failed"):
            self.provider.list_requests(params)

    # --- Test cases for get_request_diff ---
    def test_get_request_diff_success(self):
        """
        Verifies get_request_diff returns the correct diff string.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "--- a/file.txt\n+++ b/file.txt\n-old\n+new"
        self.mock_command_runner.return_value = mock_output
        params = GiteaGetRequestDiffParams(request_id="101", repository="my-repo")

        # Act
        diff = self.provider.get_request_diff(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "git",
                "obs",
                "pr",
                "show",
                "--timeline",
                "--patch",
                "my-repo#101",
            ]
        )
        self.assertEqual(diff, mock_output.stdout)

    def test_get_request_diff_error(self):
        """
        Verifies get_request_diff propagates RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Command failed")
        params = GiteaGetRequestDiffParams(request_id="101", repository="my-repo")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Command failed"):
            self.provider.get_request_diff(params)

    # --- Test cases for approve_request ---
    def test_approve_request_success(self):
        """
        Verifies approve_request for Gitea works correctly.
        """
        # Arrange
        self.mock_command_runner.return_value = MagicMock(stdout="Comment added.")
        params = GiteaApproveRequestParams(
            request_id="101", repository="my-repo", reviewer="me"
        )

        # Act
        output_lines = self.provider.approve_request(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "git",
                "obs",
                "pr",
                "comment",
                "my-repo#101",
                "-m",
                "@me: approve",
            ]
        )
        self.assertEqual(output_lines, ["Comment added."])

    def test_approve_request_error(self):
        """
        Verifies approve_request propagates RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Command failed")
        params = GiteaApproveRequestParams(
            request_id="101", repository="my-repo", reviewer="me"
        )

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Command failed"):
            self.provider.approve_request(params)


if __name__ == "__main__":
    unittest.main()


class TestGiteaReviewProviderStaticMethods(unittest.TestCase):
    """
    Unit tests for the GiteaReviewProvider static methods.
    """

    def setUp(self):
        self.mock_args = Namespace(
            repository="my-repo",
            branch="main",
            reviewer="me",
            # OBS args are not used by this provider
            project=None,
            staging=None,
            bugowner=False,
        )

    def test_build_list_params(self):
        """
        Verifies build_list_params correctly creates GiteaListRequestsParams.
        """
        params = GiteaReviewProvider.build_list_params(self.mock_args)
        self.assertIsInstance(params, GiteaListRequestsParams)
        self.assertEqual(params.repository, "my-repo")
        self.assertEqual(params.branch, "main")
        self.assertEqual(params.reviewer, "me")

    def test_build_get_request_diff_params(self):
        """
        Verifies build_get_request_diff_params correctly creates GiteaGetRequestDiffParams.
        """
        params = GiteaReviewProvider.build_get_request_diff_params(
            "101", self.mock_args
        )
        self.assertIsInstance(params, GiteaGetRequestDiffParams)
        self.assertEqual(params.request_id, "101")
        self.assertEqual(params.repository, "my-repo")

    def test_build_approve_request_params(self):
        """
        Verifies build_approve_request_params correctly creates GiteaApproveRequestParams.
        """
        params = GiteaReviewProvider.build_approve_request_params("101", self.mock_args)
        self.assertIsInstance(params, GiteaApproveRequestParams)
        self.assertEqual(params.request_id, "101")
        self.assertEqual(params.repository, "my-repo")
        self.assertEqual(params.reviewer, "me")
