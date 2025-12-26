import unittest
from unittest.mock import MagicMock, patch, call
from argparse import Namespace

from relx import packages
from relx.providers import base


class TestPackagesCLI(unittest.TestCase):
    """
    Unit tests for the relx packages CLI subcommand.
    """

    def setUp(self):
        """
        Set up common mocks and objects for tests.
        """
        self.mock_package_provider = MagicMock(spec=base.PackageProvider)
        self.mock_user_provider = MagicMock(spec=base.UserProvider)

        self.mock_args = Namespace(
            osc_instance="https://api.fake.obs",
            project="fake_project",
            product="fake_product",
            binary_name=[],
        )
        self.mock_config = {
            "default_project": "fake_project",
            "default_product": "fake_product",
            "default_productcomposer": ":product-composer",
        }

    @patch("relx.packages.get_user_provider")
    @patch("relx.packages.get_package_provider")
    @patch("relx.packages.Console")
    @patch("relx.packages.Table")
    def test_main_single_package_success(
        self,
        mock_table_class,
        mock_console_class,
        mock_get_package_provider,
        mock_get_user_provider,
    ):
        """
        Tests the main function with a single successful package lookup.
        """
        # --- Arrange ---
        self.mock_args.binary_name = ["vim"]
        mock_get_package_provider.return_value = self.mock_package_provider
        mock_get_user_provider.return_value = self.mock_user_provider

        mock_table_instance = mock_table_class.return_value
        mock_console_instance = mock_console_class.return_value

        # Mock provider return values
        self.mock_package_provider.get_source_package.return_value = "vim-source"
        self.mock_package_provider.is_shipped.return_value = True
        self.mock_package_provider.get_bugowner.return_value = (
            ["testuser"],
            False,
        )  # (owners, is_group)
        self.mock_user_provider.get_user.return_value = iter(
            [{"User": "testuser", "Email": "test@suse.com"}]
        )

        # --- Act ---
        packages.main(self.mock_args, self.mock_config)

        # --- Assert ---
        # Provider creation
        mock_get_package_provider.assert_called_once_with(
            provider_name="obs", api_url=self.mock_args.osc_instance
        )

        # Provider method calls
        self.mock_package_provider.get_source_package.assert_called_once_with(
            project="fake_project", package="vim"
        )
        self.mock_package_provider.is_shipped.assert_called_once()
        self.mock_package_provider.get_bugowner.assert_called_once_with(
            package="vim-source"
        )

        # Check that get_bugowner_info was called correctly (via get_user_provider)
        mock_get_user_provider.assert_called_once_with(
            provider_name="obs", api_url=self.mock_args.osc_instance
        )
        self.mock_user_provider.get_user.assert_called_once_with(
            search_text="testuser", search_by="login"
        )

        # Check Table and Console interactions
        mock_table_class.assert_called_once_with(title="vim", show_header=False)
        expected_rows = [
            call("Source package", "vim-source"),
            call("Shipped", "YES - fake_product"),
            call("User", "testuser"),
            call("Email", "test@suse.com"),
        ]
        mock_table_instance.add_row.assert_has_calls(expected_rows)
        mock_console_instance.print.assert_called_once_with(mock_table_instance)

    @patch("relx.packages.get_user_provider")
    @patch("relx.packages.get_package_provider")
    @patch("relx.packages.Console")
    @patch("relx.packages.Table")
    def test_main_multiple_packages(
        self,
        mock_table_class,
        mock_console_class,
        mock_get_package_provider,
        mock_get_user_provider,
    ):
        """
        Tests the main function with multiple package lookups, including one failure.
        """
        # --- Arrange ---
        self.mock_args.binary_name = ["vim", "non-existent-pkg", "nano"]
        mock_get_package_provider.return_value = self.mock_package_provider
        mock_get_user_provider.return_value = self.mock_user_provider
        mock_console_instance = mock_console_class.return_value

        # Set up side effects for multiple calls
        self.mock_package_provider.get_source_package.side_effect = [
            "vim-source",
            RuntimeError("No source package found"),  # This will be caught
            "nano-source",
        ]
        self.mock_package_provider.is_shipped.side_effect = [
            True,
            False,
        ]  # Only called for success cases
        self.mock_package_provider.get_bugowner.side_effect = [
            (["user1"], False),
            (["group1"], True),
        ]
        self.mock_user_provider.get_user.return_value = iter([{"User": "user1"}])
        self.mock_user_provider.get_group.return_value = {"Group": "group1"}

        # --- Act ---
        packages.main(self.mock_args, self.mock_config)

        # --- Assert ---
        # Verify providers are fetched
        mock_get_package_provider.assert_called_once()

        # Verify provider methods were called for each package
        self.assertEqual(self.mock_package_provider.get_source_package.call_count, 3)

        # Check interactions for successful packages (vim and nano)
        self.assertEqual(self.mock_package_provider.is_shipped.call_count, 2)
        self.assertEqual(self.mock_package_provider.get_bugowner.call_count, 2)
        self.assertEqual(self.mock_user_provider.get_user.call_count, 1)
        self.assertEqual(self.mock_user_provider.get_group.call_count, 1)

        # Check that Table was created for each package (3 times)
        self.assertEqual(mock_table_class.call_count, 3)

        # Check that console.print was called for success and failure cases
        print_calls = mock_console_instance.print.call_args_list
        self.assertEqual(len(print_calls), 3)
        # First call prints a Table
        self.assertIsInstance(print_calls[0].args[0], MagicMock)
        # Second call prints the error message
        self.assertIn("Error:", print_calls[1].args[0])
        # Third call prints a Table
        self.assertIsInstance(print_calls[2].args[0], MagicMock)

    @patch("relx.packages.get_package_provider")
    @patch("relx.packages.Console")
    def test_main_runtime_error(self, mock_console_class, mock_get_package_provider):
        """
        Tests that a RuntimeError during provider call is caught and printed.
        """
        # --- Arrange ---
        self.mock_args.binary_name = ["bad-pkg"]
        mock_get_package_provider.return_value = self.mock_package_provider
        mock_console_instance = mock_console_class.return_value

        self.mock_package_provider.get_source_package.side_effect = RuntimeError(
            "Something went wrong"
        )

        # --- Act ---
        packages.main(self.mock_args, self.mock_config)

        # --- Assert ---
        mock_console_instance.print.assert_called_once_with(
            "[bold red]Error:[/bold red] Something went wrong"
        )
