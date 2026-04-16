"""
Tests for generic table query tools.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.table_tools import QueryTableParams, query_table
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestTableTools(unittest.TestCase):
    """Tests for generic table query behavior."""

    def setUp(self):
        self.config = ServerConfig(
            instance_url="https://example.service-now.com",
            auth=AuthConfig(
                type=AuthType.BASIC,
                basic=BasicAuthConfig(username="admin", password="password"),
            ),
        )
        self.auth_manager = AuthManager(self.config.auth)
        self.auth_manager.get_headers = MagicMock(
            return_value={"Authorization": "Basic YWRtaW46cGFzc3dvcmQ="}
        )

    @patch("requests.get")
    def test_query_table_success(self, mock_get):
        """It should return table results and query metadata."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {"sys_id": "1", "name": "Agent A"},
                {"sys_id": "2", "name": "Agent B"},
            ]
        }
        mock_get.return_value = mock_response

        params = QueryTableParams(
            table="sn_aia_agent",
            query="active=true",
            limit=50,
            offset=10,
            fields=["sys_id", "name"],
            display_value="true",
        )
        result = query_table(self.config, self.auth_manager, params)

        self.assertTrue(result["success"])
        self.assertEqual(result["table"], "sn_aia_agent")
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["result"]), 2)

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], f"{self.config.api_url}/table/sn_aia_agent")
        self.assertEqual(call_args[1]["params"]["sysparm_query"], "active=true")
        self.assertEqual(call_args[1]["params"]["sysparm_limit"], "50")
        self.assertEqual(call_args[1]["params"]["sysparm_offset"], "10")
        self.assertEqual(call_args[1]["params"]["sysparm_fields"], "sys_id,name")
        self.assertEqual(call_args[1]["params"]["sysparm_display_value"], "true")

    @patch("requests.get")
    def test_query_table_invalid_table_name(self, mock_get):
        """It should reject table names that are not valid identifiers."""
        params = QueryTableParams(table="../sys_user")
        result = query_table(self.config, self.auth_manager, params)

        self.assertFalse(result["success"])
        self.assertIn("Invalid table name", result["message"])
        mock_get.assert_not_called()

    @patch("requests.get")
    def test_query_table_request_failure(self, mock_get):
        """It should surface request failures as a structured error."""
        mock_get.side_effect = requests.RequestException("network error")

        params = QueryTableParams(table="sn_aia_agent")
        result = query_table(self.config, self.auth_manager, params)

        self.assertFalse(result["success"])
        self.assertIn("Failed to query table", result["message"])


if __name__ == "__main__":
    unittest.main()
