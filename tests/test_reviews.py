import unittest
from unittest.mock import MagicMock, patch, call
from argparse import Namespace

from relx import reviews
from relx.providers import base
from relx.providers.params import (
    ObsListRequestsParams,
    GiteaListRequestsParams,
    Request,
)
from relx.exceptions import RelxUserCancelError


class TestReviewsCLI(unittest.TestCase):
    """
    Unit tests for the relx reviews CLI subcommand.
    """

    def setUp(self):
        """
        Set up common mocks and objects for tests.
        """
        self.mock_review_provider = MagicMock(spec=base.ReviewProvider)

        self.mock_args = Namespace(
            osc_instance="https://api.fake.obs",
            # OBS args
            project="fake_project",
            bugowner=False,
            staging=None,
            # Gitea args
            repository=None,
            branch=None,
            reviewer=None,
        )
        self.mock_config = {}  # Not used in reviews.main

    @patch("relx.reviews.Console")
    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.get_review_provider")
    def test_main_no_reviews(
        self, mock_get_provider, mock_print_panel, mock_console_class
    ):
        """
        Tests main function when there are no review requests.
        """
        # Arrange
        mock_get_provider.return_value = self.mock_review_provider
        self.mock_review_provider.list_requests.return_value = []

        # Act
        reviews.main(self.mock_args, self.mock_config)  # Should just return

        # Assert
        self.mock_review_provider.list_requests.assert_called_once_with(
            ObsListRequestsParams(
                project=self.mock_args.project,
                staging=self.mock_args.staging,
                is_bugowner_request=self.mock_args.bugowner,
            )
        )
        mock_print_panel.assert_called_once_with(
            ["No pending reviews."], "Request Reviews for OBS"
        )

    @patch("relx.reviews.Console")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.get_review_provider")
    def test_main_start_and_abort(
        self, mock_get_provider, mock_print_panel, mock_prompt, mock_console_class
    ):
        """
        Tests main function where user chooses not to start the review process.
        """
        # Arrange
        mock_get_provider.return_value = self.mock_review_provider
        self.mock_review_provider.list_requests.return_value = [
            Request(id="123", name="pkg1", provider_type="obs")
        ]
        mock_prompt.return_value = "n"  # User says 'n' to "Start the reviews?"

        # Act & Assert
        with self.assertRaises(RelxUserCancelError):
            reviews.main(self.mock_args, self.mock_config)

        self.mock_review_provider.list_requests.assert_called_once_with(
            ObsListRequestsParams(
                project=self.mock_args.project,
                staging=self.mock_args.staging,
                is_bugowner_request=self.mock_args.bugowner,
            )
        )
        mock_print_panel.assert_called_once_with(
            ["- SR#123: pkg1"], "Request Reviews for OBS"
        )
        mock_prompt.assert_called_once_with(
            ">>> Start the reviews (1)?", choices=["y", "n"], default="y"
        )

    @patch("relx.reviews.Console")
    @patch("relx.reviews.pager_command")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.get_review_provider")
    def test_main_full_review_and_approve(
        self,
        mock_get_provider,
        mock_print_panel,
        mock_prompt,
        mock_pager,
        mock_console_class,
    ):
        """
        Tests the full happy path: review and approve a request.
        """
        # Arrange
        mock_get_provider.return_value = self.mock_review_provider
        self.mock_review_provider.list_requests.return_value = [
            Request(id="123", name="pkg1", provider_type="obs")
        ]
        self.mock_review_provider.get_request_diff.return_value = "This is a diff"
        self.mock_review_provider.approve_request.return_value = ["Approved."]

        # Simulate user input: y (start), y (review), y (approve)
        mock_prompt.side_effect = ["y", "y", "y"]

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        self.mock_review_provider.list_requests.assert_called_once_with(
            ObsListRequestsParams(
                project=self.mock_args.project,
                staging=self.mock_args.staging,
                is_bugowner_request=self.mock_args.bugowner,
            )
        )
        self.mock_review_provider.get_request_diff.assert_called_once_with("123")
        mock_pager.assert_called_once_with(["delta"], "This is a diff")
        self.mock_review_provider.approve_request.assert_called_once_with("123", False)

        self.assertIn(call(["Approved."]), mock_print_panel.call_args_list)
        self.assertIn(call(["All reviews done."]), mock_print_panel.call_args_list)

    @patch("relx.reviews.Console")
    @patch("relx.reviews.pager_command")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.get_review_provider")
    def test_main_abort_in_loop(
        self,
        mock_get_provider,
        mock_print_panel,
        mock_prompt,
        mock_pager,
        mock_console_class,
    ):
        """
        Tests aborting the review process inside the loop.
        """
        # Arrange
        mock_get_provider.return_value = self.mock_review_provider
        self.mock_review_provider.list_requests.return_value = [
            Request(id="123", name="pkg1", provider_type="obs"),
            Request(id="124", name="pkg2", provider_type="obs"),
        ]

        # Simulate user input: y (start), a (abort on first review)
        mock_prompt.side_effect = ["y", "a"]

        # Act & Assert
        with self.assertRaises(RelxUserCancelError):
            reviews.main(self.mock_args, self.mock_config)

        self.mock_review_provider.list_requests.assert_called_once_with(
            ObsListRequestsParams(
                project=self.mock_args.project,
                staging=self.mock_args.staging,
                is_bugowner_request=self.mock_args.bugowner,
            )
        )
        mock_pager.assert_not_called()
        self.mock_review_provider.approve_request.assert_not_called()

    @patch("relx.reviews.Console")
    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.get_review_provider")
    def test_main_gitea_provider_selected(
        self, mock_get_provider, mock_prompt, mock_print_panel, mock_console_class
    ):
        """
        Tests that the Gitea provider is selected when Gitea arguments are provided.
        """
        # Arrange
        self.mock_args.project = None  # Unset OBS arg
        self.mock_args.repository = "my-repo"
        self.mock_args.branch = "main"
        self.mock_args.reviewer = "me"

        mock_get_provider.return_value = self.mock_review_provider
        self.mock_review_provider.list_requests.return_value = [
            Request(id="388", name="Forwarded PRs: plymouth", provider_type="gitea")
        ]
        mock_prompt.return_value = "n"  # Simulate user aborting

        # Act & Assert
        with self.assertRaises(RelxUserCancelError):
            reviews.main(self.mock_args, self.mock_config)

        # Assert
        mock_get_provider.assert_called_once_with(
            provider_name="gitea", api_url=self.mock_args.osc_instance
        )
        self.mock_review_provider.list_requests.assert_called_once_with(
            GiteaListRequestsParams(
                repository="my-repo",
                branch="main",
                reviewer="me",
            )
        )
        mock_print_panel.assert_called_once_with(
            ["- PR#388: Forwarded PRs: plymouth"], "Request Reviews for GITEA"
        )

    @patch("relx.reviews.Console")
    @patch("relx.reviews.get_review_provider")
    def test_main_error_on_mixed_args(self, mock_get_provider, mock_console_class):
        """
        Tests that an error is printed when both OBS and Gitea arguments are provided.
        """
        # Arrange
        self.mock_args.project = "fake-project"
        self.mock_args.repository = "my-repo"
        self.mock_args.branch = "main"
        self.mock_args.reviewer = "me"

        mock_console_instance = mock_console_class.return_value

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        mock_console_instance.print.assert_called_once_with(
            "[bold red]Error: Please provide arguments for either OBS (--project) or Gitea, not both.[/bold red]"
        )
        mock_get_provider.assert_not_called()

    @patch("relx.reviews.Console")
    @patch("relx.reviews.get_review_provider")
    def test_main_error_on_no_args(self, mock_get_provider, mock_console_class):
        """
        Tests that an error is printed when no provider arguments are provided.
        """
        # Arrange
        self.mock_args.project = None
        self.mock_args.repository = None

        mock_console_instance = mock_console_class.return_value

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        mock_console_instance.print.assert_called_once_with(
            "[bold red]Error: Please provide arguments for a provider. For OBS: --project. For Gitea: --repository, --branch, AND --reviewer.[/bold red]"
        )
        mock_get_provider.assert_not_called()
