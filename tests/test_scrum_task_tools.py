"""Tests for scrum task management tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.scrum_task_tools import create_scrum_task, update_scrum_task, list_scrum_tasks
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestScrumTaskTools(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.post")
    def test_create_scrum_task(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "st1", "short_description": "Task1"}}),
        )
        result = create_scrum_task(self.auth, self.config, {
            "story": "s1", "short_description": "Task1",
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["scrum_task"]["sys_id"], "st1")

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.post")
    def test_create_scrum_task_with_all_fields(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "st1"}}),
        )
        result = create_scrum_task(self.auth, self.config, {
            "story": "s1", "short_description": "Task1", "priority": "2",
            "planned_hours": "8", "remaining_hours": "8", "hours": "0",
            "description": "Detailed", "type": "Development", "state": "1",
            "assignment_group": "Dev", "assigned_to": "admin", "work_notes": "Starting",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.post")
    def test_create_scrum_task_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = create_scrum_task(self.auth, self.config, {"story": "s1", "short_description": "T"})
        self.assertFalse(result["success"])

    def test_create_scrum_task_missing_params(self):
        result = create_scrum_task(self.auth, self.config, {"short_description": "T"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.put")
    def test_update_scrum_task(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "st1", "state": "2"}}),
        )
        result = update_scrum_task(self.auth, self.config, {"scrum_task_id": "st1", "state": "2"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.put")
    def test_update_scrum_task_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = update_scrum_task(self.auth, self.config, {"scrum_task_id": "st1", "state": "2"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.get")
    def test_list_scrum_tasks(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "st1"}, {"sys_id": "st2"}]}),
            headers={"X-Total-Count": "2"},
        )
        result = list_scrum_tasks(self.auth, self.config, {"limit": 10})
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.get")
    def test_list_scrum_tasks_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
            headers={"X-Total-Count": "0"},
        )
        result = list_scrum_tasks(self.auth, self.config, {"state": "2", "assignment_group": "Dev"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.scrum_task_tools.requests.get")
    def test_list_scrum_tasks_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = list_scrum_tasks(self.auth, self.config, {"limit": 10})
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
