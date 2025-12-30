import os
import subprocess
import sys
import tempfile
import unittest

from relx import __version__


class TestCLI(unittest.TestCase):
    """
    Functional tests for the relx CLI entry point.
    """

    def test_version_command_succeeds_without_config(self):
        """
        Test that 'relx --version' runs successfully without a config file.
        This command should not require any configuration to be present.
        """
        # Arrange
        # We run the command in an environment where the config is guaranteed not to exist.
        with tempfile.TemporaryDirectory() as temp_home:
            env = os.environ.copy()
            env["HOME"] = temp_home
            env["XDG_CONFIG_HOME"] = os.path.join(temp_home, ".config")

            command = [sys.executable, "-m", "relx", "--version"]

            # Act
            result = subprocess.run(
                command, capture_output=True, text=True, env=env, check=False
            )

            # Assert
            self.assertEqual(result.returncode, 0, "Command should exit successfully.")
            self.assertIn(
                f"relx {__version__}",
                result.stdout,
                "The output should contain the correct version string.",
            )
            self.assertEqual(result.stderr, "", "There should be no errors on stderr.")

    def test_subcommand_fails_without_config(self):
        """
        Test that a subcommand fails with a clear error if no config file is found.
        """
        # Arrange
        # We run the command in an environment where the config is guaranteed not to exist.
        with tempfile.TemporaryDirectory() as temp_home:
            env = os.environ.copy()
            env["HOME"] = temp_home
            env["XDG_CONFIG_HOME"] = os.path.join(temp_home, ".config")

            # Using 'users' as an example subcommand
            command = [sys.executable, "-m", "relx", "users", "--login", "test"]

            # Act
            result = subprocess.run(
                command, capture_output=True, text=True, env=env, check=False
            )

            # Assert
            self.assertEqual(
                result.returncode, 1, "Command should exit with a failure code."
            )
            self.assertIn(
                "Error: Configuration file",
                result.stderr,
                "Stderr should contain the config file error.",
            )
            self.assertIn(
                "not found",
                result.stderr,
                "Stderr should contain the 'not found' message.",
            )

    def test_help_message_shows_subcommands(self):
        """
        Test that 'relx --help' shows the list of available subcommands.
        This should work even without a config file.
        """
        # Arrange
        with tempfile.TemporaryDirectory() as temp_home:
            env = os.environ.copy()
            env["HOME"] = temp_home
            env["XDG_CONFIG_HOME"] = os.path.join(temp_home, ".config")

            command = [sys.executable, "-m", "relx", "--help"]

            # Act
            result = subprocess.run(
                command, capture_output=True, text=True, env=env, check=False
            )

            # Assert
            self.assertEqual(
                result.returncode, 0, "Help command should exit successfully."
            )
            self.assertIn("usage: relx [-h]", result.stdout)
            # Check that the subcommands are listed in the help output
            self.assertIn("{artifacts,packages,reviews,users}", result.stdout)
            self.assertIn("artifacts", result.stdout)
            self.assertIn("packages", result.stdout)
            self.assertIn("reviews", result.stdout)
            self.assertIn("users", result.stdout)


if __name__ == "__main__":
    unittest.main()
