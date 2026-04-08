"""Tests for Service Catalog Task (SCTASK) tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.sctask_tools import get_sctask, list_sctasks, update_sctask
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestSCTaskTools(unittest.TestCase):

    def setUp(self):
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test", password="test"),
        )
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=self.auth_config,
        )
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {
            "Authorization": "Bearer FAKE_TOKEN",
        }

    # --- get_sctask ---

    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_get_sctask_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "abc123",
                    "number": "SCTASK0525799",
                    "short_description": "Install software",
                    "description": "Install VS Code",
                    "state": "Open",
                    "priority": "3 - Moderate",
                    "assigned_to": "John Doe",
                    "assignment_group": "Desktop Support",
                    "request_item": "RITM001",
                    "request": "REQ001",
                    "opened_at": "2025-01-01 08:00:00",
                    "closed_at": "",
                    "time_worked": "01:30:00",
                    "work_notes": "",
                    "close_notes": "",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_sctask(
            self.auth_manager, self.config, {"task_number": "SCTASK0525799"}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["sctask"]["number"], "SCTASK0525799")
        self.assertEqual(result["sctask"]["sys_id"], "abc123")
        mock_get.assert_called_once()

    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_get_sctask_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_sctask(
            self.auth_manager, self.config, {"task_number": "SCTASK9999999"}
        )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])

    def test_get_sctask_missing_param(self):
        result = get_sctask(self.auth_manager, self.config, {})

        self.assertFalse(result["success"])
        self.assertIn("task_number", result["message"])

    # --- list_sctasks ---

    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_list_sctasks_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {"sys_id": "abc123", "number": "SCTASK0001"},
                {"sys_id": "def456", "number": "SCTASK0002"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_sctasks(self.auth_manager, self.config, {"limit": 10})

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["sctasks"]), 2)

    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_list_sctasks_with_filters(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_sctasks(
            self.auth_manager,
            self.config,
            {
                "state": "2",
                "assigned_to": "john.doe",
                "assignment_group": "Desktop Support",
            },
        )

        self.assertTrue(result["success"])
        call_args = mock_get.call_args
        query = call_args[1]["params"]["sysparm_query"]
        self.assertIn("state=2", query)
        self.assertIn("john.doe", query)
        self.assertIn("Desktop Support", query)

    # --- update_sctask ---

    @patch("servicenow_mcp.tools.sctask_tools.requests.patch")
    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_update_sctask_success(self, mock_get, mock_patch):
        # Mock the lookup to resolve SCTASK number to sys_id
        lookup_response = MagicMock()
        lookup_response.json.return_value = {
            "result": [{"sys_id": "abc123"}]
        }
        lookup_response.raise_for_status = MagicMock()
        mock_get.return_value = lookup_response

        # Mock the PATCH response
        patch_response = MagicMock()
        patch_response.json.return_value = {
            "result": {
                "sys_id": "abc123",
                "number": "SCTASK0525799",
                "state": "2",
            }
        }
        patch_response.raise_for_status = MagicMock()
        mock_patch.return_value = patch_response

        result = update_sctask(
            self.auth_manager,
            self.config,
            {
                "task_number": "SCTASK0525799",
                "state": "2",
                "work_notes": "Started working on this",
            },
        )

        self.assertTrue(result["success"])
        self.assertIn("updated successfully", result["message"])
        mock_patch.assert_called_once()

    @patch("servicenow_mcp.tools.sctask_tools.requests.patch")
    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_update_sctask_time_worked_accumulation(self, mock_get, mock_patch):
        # First call: resolve SCTASK number
        lookup_response = MagicMock()
        lookup_response.json.return_value = {
            "result": [{"sys_id": "abc123"}]
        }
        lookup_response.raise_for_status = MagicMock()

        # Second call: get current time_worked
        time_response = MagicMock()
        time_response.json.return_value = {
            "result": {"time_worked": "1970-01-01 01:30:00"}
        }
        time_response.raise_for_status = MagicMock()

        mock_get.side_effect = [lookup_response, time_response]

        # Mock the PATCH response
        patch_response = MagicMock()
        patch_response.json.return_value = {
            "result": {"sys_id": "abc123", "time_worked": "03:30:00"}
        }
        patch_response.raise_for_status = MagicMock()
        mock_patch.return_value = patch_response

        result = update_sctask(
            self.auth_manager,
            self.config,
            {"task_number": "SCTASK0525799", "time_worked": "02:00:00"},
        )

        self.assertTrue(result["success"])
        # Verify the accumulated time was sent (01:30 + 02:00 = 03:30)
        patch_call = mock_patch.call_args
        self.assertEqual(patch_call[1]["json"]["time_worked"], "03:30:00")

    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_update_sctask_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = update_sctask(
            self.auth_manager,
            self.config,
            {"task_number": "SCTASK9999999", "state": "2"},
        )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])

    def test_update_sctask_missing_param(self):
        result = update_sctask(self.auth_manager, self.config, {"state": "2"})

        self.assertFalse(result["success"])
        self.assertIn("task_number", result["message"])

    # --- unwrap params ---

    @patch("servicenow_mcp.tools.sctask_tools.requests.get")
    def test_get_sctask_unwraps_nested_params(self, mock_get):
        """Test that params wrapped in {"params": {...}} are unwrapped."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [{"sys_id": "abc123", "number": "SCTASK0001"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_sctask(
            self.auth_manager,
            self.config,
            {"params": {"task_number": "SCTASK0001"}},
        )

        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
