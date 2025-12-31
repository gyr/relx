import unittest
from unittest.mock import MagicMock, call
from argparse import Namespace

from relx.providers.obs_review import OBSReviewProvider
from relx.providers.params import (
    ObsListRequestsParams,
    Request,
    ObsGetRequestDiffParams,
    ObsApproveRequestParams,
)


class TestOBSReviewProvider(unittest.TestCase):
    """
    Unit tests for the OBSReviewProvider.
    """

    def setUp(self):
        """
        Set up common mocks and the provider instance for tests.
        """
        self.mock_command_runner = MagicMock()
        self.api_url = "https://api.fake.obs"
        self.provider = OBSReviewProvider(
            api_url=self.api_url,
            command_runner=self.mock_command_runner,
        )

    # --- Test cases for list_requests ---
    def test_list_requests_default_success(self):
        """
        Verifies list_requests correctly parses default review requests.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection>
  <request id="123">
    <state name="review"/>
    <review by_group="sle-release-managers" state="new"/>
    <action type="submit">
      <target project="fake-project" package="pkg1"/>
    </action>
  </request>
  <request id="124">
    <state name="review"/>
    <review by_group="sle-release-managers" state="new"/>
    <action type="submit">
      <target project="fake-project" package="pkg2"/>
    </action>
  </request>
  <request id="125">
    <state name="declined"/> <!-- Should be filtered out -->
  </request>
  <request id="126">
    <state name="review"/>
    <review by_group="sle-release-managers" state="accepted"/> <!-- Should be filtered out -->
  </request>
</collection>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        params = ObsListRequestsParams(project="fake-project")
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                "/search/request?match=state/@name='review' and review/@state='new' and target/@project='fake-project'&withhistory=0&withfullhistory=0",
            ]
        )
        self.assertEqual(
            requests,
            [
                Request(id="123", name="pkg1", provider_type="obs"),
                Request(id="124", name="pkg2", provider_type="obs"),
            ],
        )

    def test_list_requests_staging_success(self):
        """
        Verifies list_requests correctly parses staging review requests.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection>
  <request id="127">
    <state name="review"/>
    <review by_group="sle-release-managers" state="new"/>
    <review by_project="fake-project:Staging:A" state="new"/>
    <action type="submit">
      <target project="fake-project:Staging:A" package="pkg3"/>
    </action>
  </request>
</collection>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        params = ObsListRequestsParams(project="fake-project", staging="A")
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                "/search/request?match=state/@name='review' and review/@state='new' and review/@by_project='fake-project:Staging:A'&withhistory=0&withfullhistory=0",
            ]
        )
        self.assertEqual(
            requests, [Request(id="127", name="pkg3", provider_type="obs")]
        )

    def test_list_requests_bugowner_success(self):
        """
        Verifies list_requests correctly parses bugowner review requests.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = """
<collection>
  <request id="128">
    <state name="review"/>
    <review by_group="sle-release-managers" state="new"/>
    <action type="set_bugowner">
      <target project="fake-project" package="pkg4"/>
    </action>
  </request>
</collection>
"""
        self.mock_command_runner.return_value = mock_output

        # Act
        params = ObsListRequestsParams(project="fake-project", is_bugowner_request=True)
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "api",
                "/search/request?match=state/@name='review' and action/@type='set_bugowner' and action/target/@project='fake-project'&withhistory=0&withfullhistory=0",
            ]
        )
        self.assertEqual(
            requests, [Request(id="128", name="pkg4", provider_type="obs")]
        )

    def test_list_requests_no_reviews(self):
        """
        Verifies list_requests returns an empty list when no reviews are found.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = "<collection/>"
        self.mock_command_runner.return_value = mock_output

        # Act
        params = ObsListRequestsParams(project="fake-project")
        requests = self.provider.list_requests(params)

        # Assert
        self.mock_command_runner.assert_called_once()
        self.assertEqual(requests, [])

    def test_list_requests_called_process_error(self):
        """
        Verifies that list_requests propagates RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Mocked command failed")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Mocked command failed"):
            params = ObsListRequestsParams(project="fake-project")
            self.provider.list_requests(params)

    # --- Test cases for get_request_diff ---
    def test_get_request_diff_success(self):
        """
        Verifies get_request_diff returns the correct diff string.
        """
        # Arrange
        mock_output = MagicMock()
        mock_output.stdout = (
            "--- a/pkg1.spec\n+++ b/pkg1.spec\n@@ -1,1 +1,1 @@\n-old\n+new"
        )
        self.mock_command_runner.return_value = mock_output

        # Act
        params = ObsGetRequestDiffParams(request_id="123")
        diff = self.provider.get_request_diff(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            ["osc", "-A", self.api_url, "review", "show", "-d", "123"]
        )
        self.assertEqual(diff, mock_output.stdout)

    def test_get_request_diff_error(self):
        """
        Verifies get_request_diff propagates RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Mocked command failed")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Mocked command failed"):
            params = ObsGetRequestDiffParams(request_id="123")
            self.provider.get_request_diff(params)

    # --- Test cases for approve_request ---
    def test_approve_request_default_success(self):
        """
        Verifies approve_request for default groups.
        """
        # Arrange
        self.mock_command_runner.return_value = MagicMock(
            stdout="Accepted for group sle-release-managers"
        )

        # Act
        params = ObsApproveRequestParams(request_id="123", is_bugowner=False)
        output_lines = self.provider.approve_request(params)

        # Assert
        self.mock_command_runner.assert_called_once_with(
            [
                "osc",
                "-A",
                self.api_url,
                "review",
                "accept",
                "-m",
                "OK",
                "-G",
                "sle-release-managers",
                "123",
            ]
        )
        self.assertEqual(
            output_lines,
            ["sle-release-managers: Accepted for group sle-release-managers"],
        )

    def test_approve_request_bugowner_success(self):
        """
        Verifies approve_request for bugowner groups.
        """
        # Arrange
        self.mock_command_runner.side_effect = [
            MagicMock(stdout="Accepted for group sle-release-managers"),
            MagicMock(stdout="Accepted for group sle-staging-managers"),
        ]

        # Act
        params = ObsApproveRequestParams(request_id="123", is_bugowner=True)
        output_lines = self.provider.approve_request(params)

        # Assert
        expected_calls = [
            call(
                [
                    "osc",
                    "-A",
                    self.api_url,
                    "review",
                    "accept",
                    "-m",
                    "OK",
                    "-G",
                    "sle-release-managers",
                    "123",
                ]
            ),
            call(
                [
                    "osc",
                    "-A",
                    self.api_url,
                    "review",
                    "accept",
                    "-m",
                    "OK",
                    "-G",
                    "sle-staging-managers",
                    "123",
                ]
            ),
        ]
        self.mock_command_runner.assert_has_calls(expected_calls)
        self.assertEqual(
            output_lines,
            [
                "sle-release-managers: Accepted for group sle-release-managers",
                "sle-staging-managers: Accepted for group sle-staging-managers",
            ],
        )

    def test_approve_request_error(self):
        """
        Verifies approve_request propagates RuntimeError on command error.
        """
        # Arrange
        self.mock_command_runner.side_effect = RuntimeError("Mocked command failed")

        # Act & Assert
        with self.assertRaisesRegex(RuntimeError, "Mocked command failed"):
            params = ObsApproveRequestParams(request_id="123", is_bugowner=False)
            self.provider.approve_request(params)


if __name__ == "__main__":
    unittest.main()


class TestOBSReviewProviderStaticMethods(unittest.TestCase):
    """
    Unit tests for the OBSReviewProvider static methods.
    """

    def setUp(self):
        self.mock_args = Namespace(
            project="fake-project",
            staging="A",
            bugowner=True,
            # Gitea args are not used by this provider
            repository=None,
            branch=None,
            reviewer=None,
        )

    def test_build_list_params(self):
        """
        Verifies build_list_params correctly creates ObsListRequestsParams.
        """
        params = OBSReviewProvider.build_list_params(self.mock_args)
        self.assertIsInstance(params, ObsListRequestsParams)
        self.assertEqual(params.project, "fake-project")
        self.assertEqual(params.staging, "A")
        self.assertEqual(params.is_bugowner_request, True)

    def test_build_get_request_diff_params(self):
        """
        Verifies build_get_request_diff_params correctly creates ObsGetRequestDiffParams.
        """
        params = OBSReviewProvider.build_get_request_diff_params("123", self.mock_args)
        self.assertIsInstance(params, ObsGetRequestDiffParams)
        self.assertEqual(params.request_id, "123")

    def test_build_approve_request_params(self):
        """
        Verifies build_approve_request_params correctly creates ObsApproveRequestParams.
        """
        params = OBSReviewProvider.build_approve_request_params("123", self.mock_args)
        self.assertIsInstance(params, ObsApproveRequestParams)
        self.assertEqual(params.request_id, "123")
        self.assertEqual(params.is_bugowner, True)
