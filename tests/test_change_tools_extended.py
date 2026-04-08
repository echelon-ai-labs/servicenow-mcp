"""Extended tests for change management tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.change_tools import (
    create_change_request,
    update_change_request,
    get_change_request_details,
    add_change_task,
    submit_change_for_approval,
    approve_change,
    reject_change,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestChangeToolsExtended(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    # --- create_change_request ---

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_create_change_request(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "c1", "number": "CHG001"}}),
        )
        result = create_change_request(self.auth, self.config, {
            "short_description": "Server upgrade", "type": "normal",
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["change_request"]["number"], "CHG001")

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_create_change_request_with_all_fields(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "c1", "number": "CHG002"}}),
        )
        result = create_change_request(self.auth, self.config, {
            "short_description": "DB upgrade", "type": "normal",
            "description": "Upgrade to v15", "risk": "moderate",
            "impact": "3", "category": "Hardware",
            "requested_by": "admin", "assignment_group": "DBA",
            "start_date": "2025-01-01", "end_date": "2025-01-02",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_create_change_request_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = create_change_request(self.auth, self.config, {
            "short_description": "Test", "type": "normal",
        })
        self.assertFalse(result["success"])

    # --- update_change_request ---

    @patch("servicenow_mcp.tools.change_tools.requests.put")
    def test_update_change_request(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "c1", "state": "implement"}}),
        )
        result = update_change_request(self.auth, self.config, {
            "change_id": "c1", "state": "implement",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.put")
    def test_update_change_request_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = update_change_request(self.auth, self.config, {"change_id": "c1", "state": "2"})
        self.assertFalse(result["success"])

    # --- get_change_request_details ---

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_get_change_request_details(self, mock_get):
        change_resp = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "c1", "number": "CHG001"}]}),
        )
        tasks_resp = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "t1", "short_description": "Pre-check"}]}),
        )
        mock_get.side_effect = [change_resp, tasks_resp]
        result = get_change_request_details(self.auth, self.config, {"change_id": "c1"})
        self.assertTrue(result["success"])
        self.assertIn("change_request", result)
        self.assertIn("tasks", result)

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_get_change_request_details_empty(self, mock_get):
        change_resp = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        tasks_resp = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        mock_get.side_effect = [change_resp, tasks_resp]
        result = get_change_request_details(self.auth, self.config, {"change_id": "bad_id"})
        self.assertTrue(result["success"])
        self.assertEqual(result["tasks"], [])

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_get_change_request_details_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = get_change_request_details(self.auth, self.config, {"change_id": "c1"})
        self.assertFalse(result["success"])

    # --- add_change_task ---

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_add_change_task(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "t1", "short_description": "Pre-check"}}),
        )
        result = add_change_task(self.auth, self.config, {
            "change_id": "c1", "short_description": "Pre-check",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_add_change_task_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = add_change_task(self.auth, self.config, {
            "change_id": "c1", "short_description": "Pre-check",
        })
        self.assertFalse(result["success"])

    # --- submit_change_for_approval ---

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    @patch("servicenow_mcp.tools.change_tools.requests.patch")
    def test_submit_change_for_approval(self, mock_patch, mock_post):
        mock_patch.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "c1", "state": "assess"}}),
        )
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "a1"}}),
        )
        result = submit_change_for_approval(self.auth, self.config, {
            "change_id": "c1", "approval_comments": "Ready for review",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.patch")
    def test_submit_change_for_approval_error(self, mock_patch):
        from requests.exceptions import RequestException
        mock_patch.side_effect = RequestException("fail")
        result = submit_change_for_approval(self.auth, self.config, {"change_id": "c1"})
        self.assertFalse(result["success"])

    # --- approve_change ---

    @patch("servicenow_mcp.tools.change_tools.requests.patch")
    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_approve_change(self, mock_get, mock_patch):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "a1"}]}),
        )
        mock_patch.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "a1", "state": "approved"}}),
        )
        result = approve_change(self.auth, self.config, {
            "change_id": "c1", "approval_comments": "Looks good",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_approve_change_no_approval_found(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        result = approve_change(self.auth, self.config, {"change_id": "c1"})
        self.assertFalse(result["success"])

    # --- reject_change ---

    @patch("servicenow_mcp.tools.change_tools.requests.patch")
    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_reject_change(self, mock_get, mock_patch):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "a1"}]}),
        )
        mock_patch.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "a1", "state": "rejected"}}),
        )
        result = reject_change(self.auth, self.config, {
            "change_id": "c1", "rejection_reason": "Missing rollback plan",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_reject_change_no_approval_found(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        result = reject_change(self.auth, self.config, {
            "change_id": "c1", "rejection_reason": "No plan",
        })
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
