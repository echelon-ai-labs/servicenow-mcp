"""Extended tests for workflow tools — covers uncovered paths."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.workflow_tools import (
    add_workflow_activity,
    update_workflow_activity,
    delete_workflow_activity,
    reorder_workflow_activities,
    list_workflows,
    get_workflow_details,
    list_workflow_versions,
    get_workflow_activities,
    create_workflow,
    update_workflow,
    activate_workflow,
    deactivate_workflow,
    _get_auth_and_config,
    _unwrap_params,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestWorkflowHelpers(unittest.TestCase):
    """Test helper functions for param swapping and unwrapping."""

    def test_get_auth_and_config_correct_order(self):
        auth = MagicMock(spec=AuthManager)
        config = MagicMock(spec=ServerConfig)
        a, c = _get_auth_and_config(auth, config)
        self.assertIs(a, auth)
        self.assertIs(c, config)

    def test_get_auth_and_config_swapped(self):
        auth = MagicMock(spec=AuthManager)
        config = MagicMock(spec=ServerConfig)
        a, c = _get_auth_and_config(config, auth)
        self.assertIs(a, auth)
        self.assertIs(c, config)

    def test_get_auth_and_config_duck_typed(self):
        auth = MagicMock()
        auth.get_headers = MagicMock()
        del auth.instance_url
        config = MagicMock()
        config.instance_url = "https://test.service-now.com"
        del config.get_headers
        a, c = _get_auth_and_config(auth, config)
        self.assertIs(a, auth)
        self.assertIs(c, config)

    def test_get_auth_and_config_no_headers_raises(self):
        obj1 = MagicMock(spec=[])
        obj2 = MagicMock(spec=[])
        with self.assertRaises(ValueError):
            _get_auth_and_config(obj1, obj2)

    def test_get_auth_and_config_no_instance_url_raises(self):
        obj1 = MagicMock(spec=["get_headers"])
        obj1.get_headers = MagicMock()
        obj2 = MagicMock(spec=["get_headers"])
        obj2.get_headers = MagicMock()
        with self.assertRaises(ValueError):
            _get_auth_and_config(obj1, obj2)

    def test_unwrap_params_dict(self):
        result = _unwrap_params({"name": "test"}, None)
        self.assertEqual(result, {"name": "test"})

    def test_unwrap_params_pydantic(self):
        from servicenow_mcp.tools.workflow_tools import CreateWorkflowParams
        p = CreateWorkflowParams(name="Test WF", table="incident")
        result = _unwrap_params(p, CreateWorkflowParams)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "Test WF")


class TestWorkflowToolsExtended(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    # --- add_workflow_activity (the big uncovered function) ---

    @patch("servicenow_mcp.tools.workflow_tools.requests.post")
    def test_add_workflow_activity_direct(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "act1", "name": "Approval"}}),
        )
        result = add_workflow_activity(self.auth, self.config, {
            "workflow_version_id": "wfv1", "name": "Approval",
            "activity_type": "approval", "description": "Needs approval",
        })
        self.assertIn("activity", result)
        self.assertEqual(result["activity"]["sys_id"], "act1")

    @patch("servicenow_mcp.tools.workflow_tools.requests.post")
    def test_add_workflow_activity_with_attributes(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "act2"}}),
        )
        result = add_workflow_activity(self.auth, self.config, {
            "workflow_version_id": "wfv1", "name": "Notify",
            "attributes": {"notify_type": "email"},
        })
        self.assertIn("activity", result)

    def test_add_workflow_activity_missing_version(self):
        result = add_workflow_activity(self.auth, self.config, {"name": "Test"})
        self.assertIn("error", result)

    def test_add_workflow_activity_missing_name(self):
        result = add_workflow_activity(self.auth, self.config, {"workflow_version_id": "wfv1"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.post")
    def test_add_workflow_activity_error(self, mock_post):
        mock_post.side_effect = Exception("unexpected")
        result = add_workflow_activity(self.auth, self.config, {
            "workflow_version_id": "wfv1", "name": "Test",
        })
        self.assertIn("error", result)

    # --- update_workflow_activity ---

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_update_workflow_activity_direct(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "act1", "name": "Updated"}}),
        )
        result = update_workflow_activity(self.auth, self.config, {
            "activity_id": "act1", "name": "Updated", "description": "New desc",
        })
        # Success path returns activity data or message
        self.assertIsInstance(result, dict)

    def test_update_workflow_activity_missing_id(self):
        result = update_workflow_activity(self.auth, self.config, {"name": "Test"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_update_workflow_activity_error(self, mock_put):
        mock_put.side_effect = Exception("fail")
        result = update_workflow_activity(self.auth, self.config, {"activity_id": "a1", "name": "T"})
        self.assertIn("error", result)

    # --- delete_workflow_activity ---

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_delete_workflow_activity_direct(self, mock_delete):
        mock_delete.return_value = MagicMock(raise_for_status=MagicMock(), status_code=204)
        result = delete_workflow_activity(self.auth, self.config, {"activity_id": "act1"})
        self.assertNotIn("error", result)

    def test_delete_workflow_activity_missing_id(self):
        result = delete_workflow_activity(self.auth, self.config, {})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.delete")
    def test_delete_workflow_activity_error(self, mock_delete):
        mock_delete.side_effect = Exception("fail")
        result = delete_workflow_activity(self.auth, self.config, {"activity_id": "a1"})
        self.assertIn("error", result)

    # --- reorder_workflow_activities ---

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_reorder_workflow_activities_direct(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "act1"}}),
        )
        result = reorder_workflow_activities(self.auth, self.config, {
            "activity_ids": ["act1", "act2", "act3"],
        })
        self.assertIsInstance(result, dict)

    def test_reorder_missing_ids(self):
        result = reorder_workflow_activities(self.auth, self.config, {})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_reorder_error(self, mock_put):
        mock_put.side_effect = Exception("fail")
        result = reorder_workflow_activities(self.auth, self.config, {
            "activity_ids": ["act1"],
        })
        self.assertIn("error", result)

    # --- swapped params paths ---

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_list_workflows_swapped_params(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        # Pass config first, auth second (swapped)
        result = list_workflows(self.config, self.auth, {"limit": 5})
        self.assertNotIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_get_workflow_details_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = get_workflow_details(self.auth, self.config, {"workflow_id": "wf1"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_list_workflow_versions_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = list_workflow_versions(self.auth, self.config, {"workflow_id": "wf1"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.get")
    def test_get_workflow_activities_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        result = get_workflow_activities(self.auth, self.config, {"workflow_version_id": "wfv1"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.post")
    def test_create_workflow_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        result = create_workflow(self.auth, self.config, {"name": "WF", "table": "incident"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_update_workflow_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = update_workflow(self.auth, self.config, {"workflow_id": "wf1", "name": "Updated"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_activate_workflow_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = activate_workflow(self.auth, self.config, {"workflow_id": "wf1"})
        self.assertIn("error", result)

    @patch("servicenow_mcp.tools.workflow_tools.requests.put")
    def test_deactivate_workflow_error(self, mock_put):
        from requests.exceptions import RequestException
        mock_put.side_effect = RequestException("fail")
        result = deactivate_workflow(self.auth, self.config, {"workflow_id": "wf1"})
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
