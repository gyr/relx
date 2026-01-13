import unittest
from unittest.mock import MagicMock, patch, call
from argparse import Namespace

from relx import reviews
from relx.providers.params import Request
from relx.exceptions import RelxUserCancelError


class TestReviewsCLI(unittest.TestCase):
    """
    Unit tests for the relx reviews CLI subcommand.
    """

    def setUp(self):
        """
        Set up common mocks and objects for tests.
        """
        self.mock_args = Namespace(
            osc_instance="https://api.fake.obs",
            project="fake_project",
            bugowner=False,
            staging=None,
            repository=None,
            branch=None,
            reviewer=None,
            prs=None,
            label=None,
        )
        self.mock_config = {}

    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.Console")
    @patch("relx.reviews.type")
    @patch("relx.reviews.get_review_provider")
    def test_main_no_reviews(
        self, mock_get_provider, mock_type, mock_console_class, mock_print_panel
    ):
        """
        Tests main function when there are no review requests.
        """
        # Arrange
        mock_provider_instance = MagicMock()
        mock_provider_class = MagicMock()
        mock_get_provider.return_value = mock_provider_instance
        mock_type.return_value = mock_provider_class

        mock_list_params = MagicMock()
        mock_provider_class.build_list_params.return_value = mock_list_params
        mock_provider_instance.list_requests.return_value = []

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        mock_get_provider.assert_called_once_with(
            provider_name="obs", api_url=self.mock_args.osc_instance
        )
        mock_type.assert_called_once_with(mock_provider_instance)
        mock_provider_class.build_list_params.assert_called_once_with(self.mock_args)
        mock_provider_instance.list_requests.assert_called_once_with(mock_list_params)
        mock_print_panel.assert_called_once_with(
            ["No pending reviews."], "Request Reviews for OBS"
        )

    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.Console")
    @patch("relx.reviews.type")
    @patch("relx.reviews.get_review_provider")
    def test_main_start_and_abort(
        self,
        mock_get_provider,
        mock_type,
        mock_console_class,
        mock_prompt,
        mock_print_panel,
    ):
        """
        Tests main function where user chooses not to start the review process.
        """
        # Arrange
        mock_provider_instance = MagicMock()
        mock_provider_class = MagicMock()
        mock_get_provider.return_value = mock_provider_instance
        mock_type.return_value = mock_provider_class

        mock_list_params = MagicMock()
        mock_provider_class.build_list_params.return_value = mock_list_params
        mock_provider_instance.list_requests.return_value = [
            Request(id="123", name="pkg1", provider_type="obs")
        ]
        mock_prompt.return_value = "n"

        # Act & Assert
        with self.assertRaises(RelxUserCancelError):
            reviews.main(self.mock_args, self.mock_config)

        mock_provider_class.build_list_params.assert_called_once_with(self.mock_args)
        mock_provider_instance.list_requests.assert_called_once_with(mock_list_params)

    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.pager_command")
    @patch("relx.reviews.Console")
    @patch("relx.reviews.type")
    @patch("relx.reviews.get_review_provider")
    def test_main_full_review_and_approve_obs(
        self,
        mock_get_provider,
        mock_type,
        mock_console_class,
        mock_pager,
        mock_prompt,
        mock_print_panel,
    ):
        """
        Tests the full happy path for OBS: review and approve a request.
        """
        # Arrange
        mock_provider_instance = MagicMock()
        mock_provider_class = MagicMock()
        mock_get_provider.return_value = mock_provider_instance
        mock_type.return_value = mock_provider_class

        mock_list_params = MagicMock()
        mock_diff_params = MagicMock()
        mock_approve_params = MagicMock()
        mock_provider_class.build_list_params.return_value = mock_list_params
        mock_provider_class.build_get_request_diff_params.return_value = (
            mock_diff_params
        )
        mock_provider_class.build_approve_request_params.return_value = (
            mock_approve_params
        )

        request_obj = Request(id="123", name="pkg1", provider_type="obs")
        mock_provider_instance.list_requests.return_value = [request_obj]
        mock_provider_instance.get_request_diff.return_value = "This is a diff"
        mock_provider_instance.approve_request.return_value = ["Approved."]
        mock_prompt.side_effect = ["y", "y", "y"]

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        mock_provider_class.build_list_params.assert_called_once_with(self.mock_args)
        mock_provider_instance.list_requests.assert_called_once_with(mock_list_params)
        mock_provider_class.build_get_request_diff_params.assert_called_once_with(
            "123", self.mock_args
        )
        mock_provider_instance.get_request_diff.assert_called_once_with(
            mock_diff_params
        )
        mock_provider_class.build_approve_request_params.assert_called_once_with(
            "123", self.mock_args
        )
        mock_provider_instance.approve_request.assert_called_once_with(
            mock_approve_params
        )
        self.assertIn(call(["Approved."]), mock_print_panel.call_args_list)

    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.pager_command")
    @patch("relx.reviews.Console")
    @patch("relx.reviews.type")
    @patch("relx.reviews.get_review_provider")
    def test_main_full_review_and_approve_gitea(
        self,
        mock_get_provider,
        mock_type,
        mock_console_class,
        mock_pager,
        mock_prompt,
        mock_print_panel,
    ):
        """
        Tests the full happy path for Gitea: review and approve a request.
        """
        # Arrange
        self.mock_args.project = None
        self.mock_args.repository = "my-repo"
        self.mock_args.branch = "main"
        self.mock_args.reviewer = "me"
        self.mock_args.prs = None
        self.mock_args.label = "some-label"

        mock_provider_instance = MagicMock()
        mock_provider_class = MagicMock()
        mock_get_provider.return_value = mock_provider_instance
        mock_type.return_value = mock_provider_class

        mock_list_params = MagicMock()
        mock_diff_params = MagicMock()
        mock_approve_params = MagicMock()
        mock_provider_class.build_list_params.return_value = mock_list_params
        mock_provider_class.build_get_request_diff_params.return_value = (
            mock_diff_params
        )
        mock_provider_class.build_approve_request_params.return_value = (
            mock_approve_params
        )

        request_obj = Request(id="42", name="Implement feature", provider_type="gitea")
        mock_provider_instance.list_requests.return_value = [request_obj]
        mock_provider_instance.get_request_diff.return_value = "This is a gitea diff"
        mock_provider_instance.approve_request.return_value = ["Approved."]
        mock_prompt.side_effect = ["y", "y", "y"]

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        mock_provider_class.build_list_params.assert_called_once_with(self.mock_args)
        mock_provider_instance.list_requests.assert_called_once_with(mock_list_params)
        mock_provider_class.build_get_request_diff_params.assert_called_once_with(
            "42", self.mock_args
        )
        mock_provider_instance.get_request_diff.assert_called_once_with(
            mock_diff_params
        )
        mock_provider_instance.approve_request.assert_called_once_with(
            mock_approve_params
        )
        self.assertIn(call(["Approved."]), mock_print_panel.call_args_list)

    @patch("relx.reviews.print_panel")
    @patch("relx.reviews.Prompt.ask")
    @patch("relx.reviews.pager_command")
    @patch("relx.reviews.Console")
    @patch("relx.reviews.type")
    @patch("relx.reviews.get_review_provider")
    def test_main_gitea_default_reviewer_from_config(
        self,
        mock_get_provider,
        mock_type,
        mock_console_class,
        mock_pager,
        mock_prompt,
        mock_print_panel,
    ):
        """
        Tests that Gitea reviewer is correctly taken from config if not provided in args.
        """
        # Arrange
        self.mock_args.project = None
        self.mock_args.repository = "my-repo"
        self.mock_args.branch = "main"
        self.mock_args.reviewer = None  # Explicitly not provided via CLI
        self.mock_args.prs = None
        self.mock_args.label = None

        self.mock_config = {
            "gitea": {
                "reviewer": "default_reviewer_from_config",
                "label": "default_label_from_config",
            }
        }

        mock_provider_instance = MagicMock()
        mock_provider_class = MagicMock()
        mock_get_provider.return_value = mock_provider_instance
        mock_type.return_value = mock_provider_class

        mock_list_params = MagicMock()
        mock_diff_params = MagicMock()
        mock_approve_params = MagicMock()
        mock_provider_class.build_list_params.return_value = mock_list_params
        mock_provider_class.build_get_request_diff_params.return_value = (
            mock_diff_params
        )
        mock_provider_class.build_approve_request_params.return_value = (
            mock_approve_params
        )

        request_obj = Request(id="42", name="Implement feature", provider_type="gitea")
        mock_provider_instance.list_requests.return_value = [request_obj]
        mock_provider_instance.get_request_diff.return_value = "This is a gitea diff"
        mock_provider_instance.approve_request.return_value = ["Approved."]
        mock_prompt.side_effect = ["y", "y", "y"]

        # Act
        reviews.main(self.mock_args, self.mock_config)

        # Assert
        # The reviewer should now be set in self.mock_args by the main function
        self.assertEqual(self.mock_args.reviewer, "default_reviewer_from_config")
        self.assertEqual(self.mock_args.label, "default_label_from_config")

        mock_provider_class.build_list_params.assert_called_once_with(self.mock_args)
        mock_provider_instance.list_requests.assert_called_once_with(mock_list_params)
        mock_provider_class.build_get_request_diff_params.assert_called_once_with(
            "42", self.mock_args
        )
        mock_provider_instance.get_request_diff.assert_called_once_with(
            mock_diff_params
        )
        mock_provider_class.build_approve_request_params.assert_called_once_with(
            "42", self.mock_args
        )
        mock_provider_instance.approve_request.assert_called_once_with(
            mock_approve_params
        )
        self.assertIn(call(["Approved."]), mock_print_panel.call_args_list)
