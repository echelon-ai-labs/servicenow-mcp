"""Tests for project management tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.project_tools import create_project, update_project, list_projects
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestProjectTools(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    # project_tools takes (config, auth_manager, params) — swapped order
    @patch("servicenow_mcp.tools.project_tools.requests.post")
    def test_create_project(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "p1", "short_description": "Proj1"}}),
        )
        result = create_project(self.config, self.auth, {"short_description": "Proj1"})
        self.assertTrue(result["success"])
        self.assertEqual(result["project"]["sys_id"], "p1")

    @patch("servicenow_mcp.tools.project_tools.requests.post")
    def test_create_project_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = create_project(self.config, self.auth, {"short_description": "Proj1"})
        self.assertFalse(result["success"])

    def test_create_project_missing_params(self):
        result = create_project(self.config, self.auth, {})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.project_tools.requests.put")
    def test_update_project(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "p1", "state": "2"}}),
        )
        result = update_project(self.config, self.auth, {"project_id": "p1", "state": "2"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.project_tools.requests.put")
    def test_update_project_with_all_fields(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "p1"}}),
        )
        result = update_project(self.config, self.auth, {
            "project_id": "p1", "short_description": "Updated", "status": "green",
            "state": "2", "project_manager": "admin", "percentage_complete": "50",
            "assignment_group": "PMO", "assigned_to": "admin",
            "start_date": "2025-01-01", "end_date": "2025-12-31",
        })
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.project_tools.requests.put")
    def test_update_project_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = update_project(self.config, self.auth, {"project_id": "p1", "state": "2"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.project_tools.requests.get")
    def test_list_projects(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "p1"}]}),
            headers={"X-Total-Count": "1"},
        )
        result = list_projects(self.config, self.auth, {"limit": 10})
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)

    @patch("servicenow_mcp.tools.project_tools.requests.get")
    def test_list_projects_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
            headers={"X-Total-Count": "0"},
        )
        result = list_projects(self.config, self.auth, {"state": "2", "assignment_group": "PMO"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.project_tools.requests.get")
    def test_list_projects_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = list_projects(self.config, self.auth, {"limit": 10})
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
