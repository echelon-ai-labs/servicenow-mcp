"""
Extended tests for changeset_tools.py targeting uncovered error paths.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests as requests_lib

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.changeset_tools import (
    GetChangesetDetailsParams,
    ListChangesetsParams,
    UpdateChangesetParams,
    _get_headers,
    _get_instance_url,
    _unwrap_and_validate_params,
    add_file_to_changeset,
    commit_changeset,
    create_changeset,
    get_changeset_details,
    list_changesets,
    publish_changeset,
    update_changeset,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


def _make_setup():
    auth_config = AuthConfig(
        type=AuthType.BASIC,
        basic=BasicAuthConfig(username="u", password="p"),
    )
    server_config = ServerConfig(
        instance_url="https://test.service-now.com",
        auth=auth_config,
    )
    auth_manager = MagicMock(spec=AuthManager)
    auth_manager.get_headers.return_value = {"Authorization": "Bearer test"}
    return auth_manager, server_config


# ---------------------------------------------------------------------------
# _unwrap_and_validate_params
# ---------------------------------------------------------------------------

class TestUnwrapAndValidateParams(unittest.TestCase):

    def test_wrong_pydantic_model_converts_via_dict(self):
        """Lines 101-105: params is a Pydantic model of wrong type, converts via .dict()."""
        # Pass a ListChangesetsParams where GetChangesetDetailsParams is expected
        wrong_model = ListChangesetsParams(limit=5)
        # This will fail because GetChangesetDetailsParams requires changeset_id
        result = _unwrap_and_validate_params(wrong_model, GetChangesetDetailsParams)
        self.assertFalse(result["success"])
        self.assertIn("message", result)

    def test_correct_pydantic_model_passes_through(self):
        """Lines 99-102: params is already the correct model class."""
        model = GetChangesetDetailsParams(changeset_id="abc123")
        result = _unwrap_and_validate_params(model, GetChangesetDetailsParams)
        self.assertTrue(result["success"])
        self.assertEqual(result["params"].changeset_id, "abc123")

    def test_required_field_missing_returns_error(self):
        """Lines 116-122: required field check fails."""
        model = UpdateChangesetParams(changeset_id="123", name="Test")
        result = _unwrap_and_validate_params(
            model, UpdateChangesetParams, required_fields=["state"]
        )
        self.assertFalse(result["success"])
        self.assertIn("state", result["message"])

    def test_exception_in_params_returns_error(self):
        """Lines 128-132: passing invalid dict raises exception internally."""
        # Pass a non-dict, non-model that will cause an error
        result = _unwrap_and_validate_params(
            {"invalid_field": "value"}, GetChangesetDetailsParams
        )
        self.assertFalse(result["success"])
        self.assertIn("parameters", result["message"])


# ---------------------------------------------------------------------------
# _get_instance_url
# ---------------------------------------------------------------------------

class TestGetInstanceUrl(unittest.TestCase):

    def test_falls_back_to_auth_manager_instance_url(self):
        """Lines 151-152: auth_manager has instance_url, server_config does not."""
        auth_manager = MagicMock()
        del auth_manager.instance_url  # Remove instance_url from auth_manager spec
        auth_manager2 = MagicMock()
        auth_manager2.instance_url = "https://from-auth.service-now.com"
        # server_config has no instance_url
        server_config2 = MagicMock(spec=[])
        result = _get_instance_url(auth_manager2, server_config2)
        self.assertEqual(result, "https://from-auth.service-now.com")

    def test_returns_none_when_neither_has_url(self):
        """Lines 160-161: neither object has instance_url → returns None."""
        auth_manager = MagicMock(spec=[])
        server_config = MagicMock(spec=[])
        result = _get_instance_url(auth_manager, server_config)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# _get_headers
# ---------------------------------------------------------------------------

class TestGetHeaders(unittest.TestCase):

    def test_falls_back_to_server_config_get_headers(self):
        """Lines 180-181: auth_manager has no get_headers, server_config does."""
        auth_manager = MagicMock(spec=[])  # no get_headers
        server_config = MagicMock()
        server_config.get_headers.return_value = {"X-From": "server_config"}
        result = _get_headers(auth_manager, server_config)
        self.assertEqual(result["X-From"], "server_config")

    def test_returns_none_when_neither_has_get_headers(self):
        """Lines 188-189: neither has get_headers → returns None."""
        auth_manager = MagicMock(spec=[])
        server_config = MagicMock(spec=[])
        result = _get_headers(auth_manager, server_config)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# list_changesets error paths
# ---------------------------------------------------------------------------

class TestListChangesetsErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 212: _unwrap_and_validate_params fails."""
        result = list_changesets(self.auth_manager, self.server_config, {"limit": "not-an-int"})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 219: _get_instance_url returns None."""
        bad_server_config = MagicMock(spec=[])
        result = list_changesets(self.auth_manager, bad_server_config, {})
        self.assertFalse(result["success"])
        self.assertIn("instance_url", result["message"])

    def test_no_headers_returns_error(self):
        """Line 227: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = list_changesets(bad_auth, self.server_config, {})
        self.assertFalse(result["success"])
        self.assertIn("get_headers", result["message"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.get")
    def test_timeframe_last_week(self, mock_get):
        """Line 253: timeframe='last_week' appends the correct query part."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        list_changesets(self.auth_manager, self.server_config, {"timeframe": "last_week"})
        _, kwargs = mock_get.call_args
        self.assertIn("beginningOfLastWeek", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.get")
    def test_timeframe_last_month(self, mock_get):
        """Line 255-256: timeframe='last_month' appends correct query part."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        list_changesets(self.auth_manager, self.server_config, {"timeframe": "last_month"})
        _, kwargs = mock_get.call_args
        self.assertIn("beginningOfLastMonth", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.get")
    def test_extra_query_param(self, mock_get):
        """Line 259: extra query string appended."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        list_changesets(self.auth_manager, self.server_config, {"query": "name=mycs"})
        _, kwargs = mock_get.call_args
        self.assertIn("name=mycs", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.get")
    def test_request_exception(self, mock_get):
        """Lines 278-280: RequestException returns error dict."""
        mock_get.side_effect = requests_lib.exceptions.RequestException("network err")
        result = list_changesets(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])
        self.assertIn("network err", result["message"])


# ---------------------------------------------------------------------------
# get_changeset_details error paths
# ---------------------------------------------------------------------------

class TestGetChangesetDetailsErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 310: _unwrap_and_validate_params fails (missing required changeset_id)."""
        result = get_changeset_details(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 317: _get_instance_url returns None."""
        bad_server_config = MagicMock(spec=[])
        result = get_changeset_details(bad_server_config, self.auth_manager, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    def test_no_headers_returns_error(self):
        """Line 325: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = get_changeset_details(bad_auth, self.server_config, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.get")
    def test_request_exception(self, mock_get):
        """Lines 360-362: RequestException returns error dict."""
        mock_get.side_effect = requests_lib.exceptions.RequestException("conn err")
        result = get_changeset_details(
            self.auth_manager, self.server_config, {"changeset_id": "abc"}
        )
        self.assertFalse(result["success"])
        self.assertIn("conn err", result["message"])


# ---------------------------------------------------------------------------
# create_changeset error paths
# ---------------------------------------------------------------------------

class TestCreateChangesetErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 392: _unwrap_and_validate_params fails."""
        result = create_changeset(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 411: _get_instance_url returns None."""
        bad_server = MagicMock(spec=[])
        result = create_changeset(
            bad_server, self.auth_manager, {"name": "CS", "application": "App"}
        )
        self.assertFalse(result["success"])

    def test_no_headers_returns_error(self):
        """Line 419: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = create_changeset(
            bad_auth, self.server_config, {"name": "CS", "application": "App"}
        )
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.post")
    def test_request_exception(self, mock_post):
        """Lines 441-443: RequestException returns error dict."""
        mock_post.side_effect = requests_lib.exceptions.RequestException("timeout")
        result = create_changeset(
            self.auth_manager,
            self.server_config,
            {"name": "CS", "application": "App"},
        )
        self.assertFalse(result["success"])
        self.assertIn("timeout", result["message"])


# ---------------------------------------------------------------------------
# update_changeset error paths
# ---------------------------------------------------------------------------

class TestUpdateChangesetErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 473: missing changeset_id."""
        result = update_changeset(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 484: _get_instance_url returns None."""
        bad_server = MagicMock(spec=[])
        result = update_changeset(bad_server, self.auth_manager, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    def test_no_headers_returns_error(self):
        """Line 488: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = update_changeset(bad_auth, self.server_config, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    def test_no_update_fields_returns_error(self):
        """Line 500: no update fields provided."""
        result = update_changeset(
            self.auth_manager, self.server_config, {"changeset_id": "123"}
        )
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.patch")
    def test_optional_fields_included(self, mock_patch):
        """Lines 492, 508: description and developer optional fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"sys_id": "123"}}
        mock_response.raise_for_status.return_value = None
        mock_patch.return_value = mock_response

        result = update_changeset(
            self.auth_manager,
            self.server_config,
            {"changeset_id": "123", "description": "desc", "developer": "dev"},
        )
        self.assertTrue(result["success"])
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["json"]["description"], "desc")
        self.assertEqual(kwargs["json"]["developer"], "dev")

    @patch("servicenow_mcp.tools.changeset_tools.requests.patch")
    def test_request_exception(self, mock_patch):
        """Lines 530-532: RequestException returns error dict."""
        mock_patch.side_effect = requests_lib.exceptions.RequestException("timeout")
        result = update_changeset(
            self.auth_manager,
            self.server_config,
            {"changeset_id": "123", "name": "CS"},
        )
        self.assertFalse(result["success"])
        self.assertIn("timeout", result["message"])


# ---------------------------------------------------------------------------
# commit_changeset error paths
# ---------------------------------------------------------------------------

class TestCommitChangesetErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 562: missing changeset_id."""
        result = commit_changeset(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 578: _get_instance_url returns None."""
        bad_server = MagicMock(spec=[])
        result = commit_changeset(bad_server, self.auth_manager, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    def test_no_headers_returns_error(self):
        """Line 586: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = commit_changeset(bad_auth, self.server_config, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.patch")
    def test_request_exception(self, mock_patch):
        """Lines 608-610: RequestException returns error dict."""
        mock_patch.side_effect = requests_lib.exceptions.RequestException("err")
        result = commit_changeset(
            self.auth_manager, self.server_config, {"changeset_id": "123"}
        )
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# publish_changeset error paths
# ---------------------------------------------------------------------------

class TestPublishChangesetErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 640: missing changeset_id."""
        result = publish_changeset(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 647: _get_instance_url returns None."""
        bad_server = MagicMock(spec=[])
        result = publish_changeset(bad_server, self.auth_manager, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    def test_no_headers_returns_error(self):
        """Line 655: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = publish_changeset(bad_auth, self.server_config, {"changeset_id": "123"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.patch")
    def test_request_exception(self, mock_patch):
        """Lines 686-688: RequestException returns error dict."""
        mock_patch.side_effect = requests_lib.exceptions.RequestException("err")
        result = publish_changeset(
            self.auth_manager, self.server_config, {"changeset_id": "123"}
        )
        self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# add_file_to_changeset error paths
# ---------------------------------------------------------------------------

class TestAddFileToChangesetErrors(unittest.TestCase):

    def setUp(self):
        self.auth_manager, self.server_config = _make_setup()

    def test_invalid_params_returns_error(self):
        """Line 718: missing required fields."""
        result = add_file_to_changeset(self.auth_manager, self.server_config, {})
        self.assertFalse(result["success"])

    def test_no_instance_url_returns_error(self):
        """Line 725: _get_instance_url returns None."""
        bad_server = MagicMock(spec=[])
        result = add_file_to_changeset(
            bad_server,
            self.auth_manager,
            {"changeset_id": "123", "file_path": "f.py", "file_content": "x"},
        )
        self.assertFalse(result["success"])

    def test_no_headers_returns_error(self):
        """Line 733: _get_headers returns None."""
        bad_auth = MagicMock(spec=[])
        result = add_file_to_changeset(
            bad_auth,
            self.server_config,
            {"changeset_id": "123", "file_path": "f.py", "file_content": "x"},
        )
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.changeset_tools.requests.post")
    def test_request_exception(self, mock_post):
        """Lines 763-765: RequestException returns error dict."""
        mock_post.side_effect = requests_lib.exceptions.RequestException("err")
        result = add_file_to_changeset(
            self.auth_manager,
            self.server_config,
            {"changeset_id": "123", "file_path": "f.py", "file_content": "content"},
        )
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
