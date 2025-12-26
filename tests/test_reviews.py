import unittest
from unittest.mock import MagicMock, patch, call
from argparse import Namespace

from relx import reviews
from relx.providers import base


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
            project="fake_project",
            bugowner=False,
            staging=None,
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

        # Act & Assert
        with self.assertRaises(SystemExit) as cm:
            reviews.main(self.mock_args, self.mock_config)

        self.assertEqual(cm.exception.code, 0)
        self.mock_review_provider.list_requests.assert_called_once()
        mock_print_panel.assert_called_once_with(
            ["No pending reviews."], "Request Reviews"
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
        self.mock_review_provider.list_requests.return_value = [("123", "pkg1")]
        mock_prompt.return_value = "n"  # User says 'n' to "Start the reviews?"

        # Act & Assert
        with self.assertRaises(SystemExit) as cm:
            reviews.main(self.mock_args, self.mock_config)

        self.assertEqual(cm.exception.code, 0)
        mock_print_panel.assert_called_once_with(["- SR#123: pkg1"], "Request Reviews")
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
        self.mock_review_provider.list_requests.return_value = [("123", "pkg1")]
        self.mock_review_provider.get_request_diff.return_value = "This is a diff"
        self.mock_review_provider.approve_request.return_value = ["Approved."]

        # Simulate user input: y (start), y (review), y (approve)
        mock_prompt.side_effect = ["y", "y", "y"]

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
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
            ("123", "pkg1"),
            ("124", "pkg2"),
        ]

        # Simulate user input: y (start), a (abort on first review)
        mock_prompt.side_effect = ["y", "a"]

        # Act & Assert
        with self.assertRaises(SystemExit) as cm:
            reviews.main(self.mock_args, self.mock_config)

        self.assertEqual(cm.exception.code, 0)
        mock_pager.assert_not_called()
        self.mock_review_provider.approve_request.assert_not_called()
