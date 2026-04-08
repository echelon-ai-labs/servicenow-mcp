"""Extended tests for incident management tools (create, update, comment, resolve, list)."""

import unittest
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.incident_tools import (
    CreateIncidentParams,
    UpdateIncidentParams,
    AddCommentParams,
    ResolveIncidentParams,
    ListIncidentsParams,
    create_incident,
    update_incident,
    add_comment,
    resolve_incident,
    list_incidents,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestIncidentToolsExtended(unittest.TestCase):

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://dev12345.service-now.com",
            auth=AuthConfig(type=AuthType.BASIC, basic=BasicAuthConfig(username="test", password="test")),
        )
        self.auth = MagicMock(spec=AuthManager)
        self.auth.get_headers.return_value = {"Authorization": "Bearer FAKE"}

    # --- create_incident ---

    @patch("servicenow_mcp.tools.incident_tools.requests.post")
    def test_create_incident(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "inc1", "number": "INC0010001"}}),
        )
        params = CreateIncidentParams(short_description="Server down", category="Hardware")
        result = create_incident(self.config, self.auth, params)
        self.assertTrue(result.success)
        self.assertEqual(result.incident_number, "INC0010001")

    @patch("servicenow_mcp.tools.incident_tools.requests.post")
    def test_create_incident_with_all_fields(self, mock_post):
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "inc1", "number": "INC0010002"}}),
        )
        params = CreateIncidentParams(
            short_description="Email down", description="Outlook not working",
            caller_id="user1", category="Software", subcategory="Email",
            priority="1", impact="1", urgency="1",
            assigned_to="admin", assignment_group="IT Support",
        )
        result = create_incident(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.incident_tools.requests.post")
    def test_create_incident_error(self, mock_post):
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException("fail")
        params = CreateIncidentParams(short_description="Test")
        result = create_incident(self.config, self.auth, params)
        self.assertFalse(result.success)

    # --- update_incident ---

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_update_incident_by_number(self, mock_get, mock_put):
        # Lookup by number
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "inc1"}]}),
        )
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "inc1", "number": "INC0010001"}}),
        )
        params = UpdateIncidentParams(incident_id="INC0010001", state="2")
        result = update_incident(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    def test_update_incident_by_sysid(self, mock_put):
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "a" * 32, "number": "INC001"}}),
        )
        params = UpdateIncidentParams(incident_id="a" * 32, state="2")
        result = update_incident(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_update_incident_error(self, mock_get, mock_put):
        from requests.exceptions import RequestException
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "inc1"}]}),
        )
        mock_put.side_effect = RequestException("fail")
        params = UpdateIncidentParams(incident_id="INC001", state="2")
        result = update_incident(self.config, self.auth, params)
        self.assertFalse(result.success)

    # --- add_comment ---

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_add_comment(self, mock_get, mock_put):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "inc1"}]}),
        )
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "inc1", "number": "INC001"}}),
        )
        params = AddCommentParams(incident_id="INC001", comment="Looking into it")
        result = add_comment(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_add_work_note(self, mock_get, mock_put):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "inc1"}]}),
        )
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "inc1", "number": "INC001"}}),
        )
        params = AddCommentParams(incident_id="INC001", comment="Internal note", is_work_note=True)
        result = add_comment(self.config, self.auth, params)
        self.assertTrue(result.success)

    # --- resolve_incident ---

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_resolve_incident(self, mock_get, mock_put):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "inc1"}]}),
        )
        mock_put.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": {"sys_id": "inc1", "number": "INC001"}}),
        )
        params = ResolveIncidentParams(
            incident_id="INC001", resolution_code="Solved", resolution_notes="Restarted the server",
        )
        result = resolve_incident(self.config, self.auth, params)
        self.assertTrue(result.success)

    @patch("servicenow_mcp.tools.incident_tools.requests.put")
    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_resolve_incident_error(self, mock_get, mock_put):
        from requests.exceptions import RequestException
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"sys_id": "inc1"}]}),
        )
        mock_put.side_effect = RequestException("fail")
        params = ResolveIncidentParams(
            incident_id="INC001", resolution_code="Solved", resolution_notes="Fixed",
        )
        result = resolve_incident(self.config, self.auth, params)
        self.assertFalse(result.success)

    # --- list_incidents ---

    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_list_incidents(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [
                {"sys_id": "i1", "number": "INC001", "short_description": "Test",
                 "description": "", "state": "1", "priority": "3",
                 "assigned_to": "admin", "category": "Software", "subcategory": "OS",
                 "sys_created_on": "2025-01-01", "sys_updated_on": "2025-01-02"},
            ]}),
        )
        params = ListIncidentsParams(limit=10)
        result = list_incidents(self.config, self.auth, params)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["incidents"]), 1)

    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_list_incidents_with_filters(self, mock_get):
        mock_get.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": []}),
        )
        params = ListIncidentsParams(state="1", assigned_to="admin", category="Hardware", query="priority=1")
        result = list_incidents(self.config, self.auth, params)
        self.assertTrue(result["success"])

    @patch("servicenow_mcp.tools.incident_tools.requests.get")
    def test_list_incidents_error(self, mock_get):
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("fail")
        params = ListIncidentsParams(limit=10)
        result = list_incidents(self.config, self.auth, params)
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
