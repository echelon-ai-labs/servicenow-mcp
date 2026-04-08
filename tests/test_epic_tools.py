"""Tests for epic management tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.epic_tools import create_epic, update_epic, list_epics
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestEpicTools(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    @patch("servicenow_mcp.tools.epic_tools.requests.post")
    def test_create_epic(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "e1", "short_description": "Epic1"}}),
        )
        result = create_epic(self.auth, self.config, {"short_description": "Epic1"})
        self.assertTrue(result["success"])
        self.assertEqual(result["epic"]["sys_id"], "e1")

    @patch("servicenow_mcp.tools.epic_tools.requests.post")
    def test_create_epic_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = create_epic(self.auth, self.config, {"short_description": "Epic1"})
        self.assertFalse(result["success"])

    def test_create_epic_missing_params(self):
        result = create_epic(self.auth, self.config, {})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.epic_tools.requests.put")
    def test_update_epic(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "e1", "state": "2"}}),
        )
        result = update_epic(self.auth, self.config, {"epic_id": "e1", "state": "2"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.epic_tools.requests.put")
    def test_update_epic_with_all_fields(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "e1"}}),
        )
        result = update_epic(self.auth, self.config, {
            "epic_id": "e1", "short_description": "Updated", "priority": "1",
            "state": "3", "assignment_group": "Dev", "assigned_to": "admin", "work_notes": "done",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.epic_tools.requests.put")
    def test_update_epic_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = update_epic(self.auth, self.config, {"epic_id": "e1", "state": "2"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.epic_tools.requests.get")
    def test_list_epics(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "e1"}, {"sys_id": "e2"}]}),
            headers={"X-Total-Count": "2"},
        )
        result = list_epics(self.auth, self.config, {"limit": 10})
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    @patch("servicenow_mcp.tools.epic_tools.requests.get")
    def test_list_epics_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
            headers={"X-Total-Count": "0"},
        )
        result = list_epics(self.auth, self.config, {"priority": "1", "assignment_group": "Dev"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.epic_tools.requests.get")
    def test_list_epics_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = list_epics(self.auth, self.config, {"limit": 10})
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
