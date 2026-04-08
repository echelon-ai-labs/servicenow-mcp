"""Tests for Time Card tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.time_card_tools import (
    create_time_card,
    list_time_cards,
    update_time_card,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestTimeCardTools(unittest.TestCase):

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

    # --- list_time_cards ---

    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_list_time_cards_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "tc001",
                    "task": "SCTASK0001",
                    "user": "john.doe",
                    "week_start": "2025-01-06",
                    "short_description": "Dev work",
                    "state": "Submitted",
                    "monday": "8",
                    "tuesday": "8",
                    "wednesday": "8",
                    "thursday": "8",
                    "friday": "8",
                    "saturday": "0",
                    "sunday": "0",
                    "total": "40",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_time_cards(self.auth_manager, self.config, {"limit": 10})

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["time_cards"][0]["sys_id"], "tc001")
        self.assertEqual(result["time_cards"][0]["monday"], "8")

    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_list_time_cards_by_task(self, mock_get):
        """Test filtering by task number resolves to sys_id first."""
        # First call: resolve task number
        resolve_response = MagicMock()
        resolve_response.json.return_value = {
            "result": [{"sys_id": "task_abc"}]
        }
        resolve_response.raise_for_status = MagicMock()

        # Second call: list time cards
        list_response = MagicMock()
        list_response.json.return_value = {"result": []}
        list_response.raise_for_status = MagicMock()

        mock_get.side_effect = [resolve_response, list_response]

        result = list_time_cards(
            self.auth_manager,
            self.config,
            {"task_number": "SCTASK0001"},
        )

        self.assertTrue(result["success"])
        # Verify the second call used the resolved sys_id in the query
        second_call = mock_get.call_args_list[1]
        query = second_call[1]["params"]["sysparm_query"]
        self.assertIn("task=task_abc", query)

    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_list_time_cards_task_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_time_cards(
            self.auth_manager,
            self.config,
            {"task_number": "SCTASK9999999"},
        )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])

    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_list_time_cards_by_user_and_week(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_time_cards(
            self.auth_manager,
            self.config,
            {"user": "john.doe", "week_start": "2025-01-06"},
        )

        self.assertTrue(result["success"])
        call_args = mock_get.call_args
        query = call_args[1]["params"]["sysparm_query"]
        self.assertIn("john.doe", query)
        self.assertIn("2025-01-06", query)

    # --- create_time_card ---

    @patch("servicenow_mcp.tools.time_card_tools.requests.post")
    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_create_time_card_success(self, mock_get, mock_post):
        # Mock task resolution
        resolve_response = MagicMock()
        resolve_response.json.return_value = {
            "result": [{"sys_id": "task_abc"}]
        }
        resolve_response.raise_for_status = MagicMock()
        mock_get.return_value = resolve_response

        # Mock POST response
        post_response = MagicMock()
        post_response.json.return_value = {
            "result": {
                "sys_id": "tc_new",
                "task": "task_abc",
                "user": "john.doe",
                "week_start": "2025-01-06",
                "monday": "8",
                "tuesday": "4",
                "wednesday": "0",
                "thursday": "0",
                "friday": "0",
                "saturday": "0",
                "sunday": "0",
                "total": "12",
                "short_description": "Sprint work",
                "state": "Pending",
            }
        }
        post_response.raise_for_status = MagicMock()
        mock_post.return_value = post_response

        result = create_time_card(
            self.auth_manager,
            self.config,
            {
                "task_number": "SCTASK0001",
                "week_start": "2025-01-06",
                "monday": 8,
                "tuesday": 4,
                "short_description": "Sprint work",
            },
        )

        self.assertTrue(result["success"])
        self.assertIn("created successfully", result["message"])
        self.assertEqual(result["time_card"]["sys_id"], "tc_new")

        # Verify POST payload
        post_call = mock_post.call_args
        self.assertEqual(post_call[1]["json"]["task"], "task_abc")
        self.assertEqual(post_call[1]["json"]["monday"], 8)
        self.assertEqual(post_call[1]["json"]["tuesday"], 4)
        self.assertEqual(post_call[1]["json"]["wednesday"], 0)

    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_create_time_card_task_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = create_time_card(
            self.auth_manager,
            self.config,
            {"task_number": "SCTASK9999999", "week_start": "2025-01-06"},
        )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])

    def test_create_time_card_missing_params(self):
        result = create_time_card(
            self.auth_manager, self.config, {"task_number": "SCTASK0001"}
        )

        self.assertFalse(result["success"])
        self.assertIn("week_start", result["message"])

    # --- update_time_card ---

    @patch("servicenow_mcp.tools.time_card_tools.requests.patch")
    def test_update_time_card_success(self, mock_patch):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "tc001",
                "task": "SCTASK0001",
                "monday": "8",
                "tuesday": "8",
                "wednesday": "6",
                "thursday": "0",
                "friday": "0",
                "saturday": "0",
                "sunday": "0",
                "total": "22",
                "state": "Pending",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_patch.return_value = mock_response

        result = update_time_card(
            self.auth_manager,
            self.config,
            {
                "time_card_sys_id": "tc001",
                "wednesday": 6,
                "short_description": "Updated hours",
            },
        )

        self.assertTrue(result["success"])
        self.assertIn("updated successfully", result["message"])

        # Verify only changed fields were sent
        patch_call = mock_patch.call_args
        self.assertEqual(patch_call[1]["json"]["wednesday"], 6)
        self.assertEqual(
            patch_call[1]["json"]["short_description"], "Updated hours"
        )

    @patch("servicenow_mcp.tools.time_card_tools.requests.patch")
    def test_update_time_card_state(self, mock_patch):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"sys_id": "tc001", "state": "Submitted"}
        }
        mock_response.raise_for_status = MagicMock()
        mock_patch.return_value = mock_response

        result = update_time_card(
            self.auth_manager,
            self.config,
            {"time_card_sys_id": "tc001", "state": "Submitted"},
        )

        self.assertTrue(result["success"])
        patch_call = mock_patch.call_args
        self.assertEqual(patch_call[1]["json"]["state"], "Submitted")

    def test_update_time_card_missing_sys_id(self):
        result = update_time_card(
            self.auth_manager, self.config, {"monday": 8}
        )

        self.assertFalse(result["success"])
        self.assertIn("time_card_sys_id", result["message"])

    # --- param unwrapping ---

    @patch("servicenow_mcp.tools.time_card_tools.requests.get")
    def test_list_time_cards_unwraps_nested_params(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_time_cards(
            self.auth_manager,
            self.config,
            {"params": {"limit": 5}},
        )

        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
