"""Tests for story management tools."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.story_tools import (
    create_story,
    update_story,
    list_stories,
    list_story_dependencies,
    create_story_dependency,
    delete_story_dependency,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestStoryTools(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    @patch("servicenow_mcp.tools.story_tools.requests.post")
    def test_create_story(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "s1", "number": "STY001", "short_description": "Test"}}),
        )
        result = create_story(self.auth, self.config, {"short_description": "Test", "acceptance_criteria": "Done when tested"})
        self.assertTrue(result["success"])
        self.assertEqual(result["story"]["sys_id"], "s1")

    @patch("servicenow_mcp.tools.story_tools.requests.post")
    def test_create_story_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = create_story(self.auth, self.config, {"short_description": "Test", "acceptance_criteria": "AC"})
        self.assertFalse(result["success"])

    def test_create_story_missing_params(self):
        result = create_story(self.auth, self.config, {})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.put")
    def test_update_story(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "s1", "state": "2"}}),
        )
        result = update_story(self.auth, self.config, {"story_id": "s1", "state": "2"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.put")
    def test_update_story_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = update_story(self.auth, self.config, {"story_id": "s1", "state": "2"})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.get")
    def test_list_stories(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "s1"}, {"sys_id": "s2"}]}),
            headers={"X-Total-Count": "2"},
        )
        result = list_stories(self.auth, self.config, {"limit": 10})
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    @patch("servicenow_mcp.tools.story_tools.requests.get")
    def test_list_stories_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
            headers={"X-Total-Count": "0"},
        )
        result = list_stories(self.auth, self.config, {"state": "2", "assignment_group": "Dev"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.get")
    def test_list_stories_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = list_stories(self.auth, self.config, {"limit": 10})
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.get")
    def test_list_story_dependencies(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "d1"}]}),
            headers={"X-Total-Count": "1"},
        )
        result = list_story_dependencies(self.auth, self.config, {"limit": 10})
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)

    @patch("servicenow_mcp.tools.story_tools.requests.post")
    def test_create_story_dependency(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "d1"}}),
        )
        result = create_story_dependency(self.auth, self.config, {"dependent_story": "s1", "prerequisite_story": "s2"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.delete")
    def test_delete_story_dependency(self, mock_delete):
        mock_delete.return_value = MagicMock(raise_for_status=MagicMock(), status_code=204)
        result = delete_story_dependency(self.auth, self.config, {"dependency_id": "d1"})
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.story_tools.requests.delete")
    def test_delete_story_dependency_error(self, mock_delete):
        from requests.exceptions import RequestException
        mock_delete.side_effect = RequestException("fail")
        result = delete_story_dependency(self.auth, self.config, {"dependency_id": "d1"})
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
