"""
Tests for the change management tools.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.change_tools import (
    create_change_request,
    list_change_requests,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestChangeTools(unittest.TestCase):
    """Tests for the change management tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test_user", password="test_password"),
        )
        self.server_config = ServerConfig(
            instance_url="https://test.service-now.com",
            auth=self.auth_config,
        )
        self.auth_manager = AuthManager(self.auth_config)

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_list_change_requests_success(self, mock_get):
        """Test listing change requests successfully."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "change123",
                    "number": "CHG0010001",
                    "short_description": "Test Change",
                    "type": "normal",
                    "state": "open",
                },
                {
                    "sys_id": "change456",
                    "number": "CHG0010002",
                    "short_description": "Another Test Change",
                    "type": "emergency",
                    "state": "in progress",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the function
        params = {
            "limit": 10,
            "timeframe": "upcoming",
        }
        result = list_change_requests(self.auth_manager, self.server_config, params)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(len(result["change_requests"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["change_requests"][0]["sys_id"], "change123")
        self.assertEqual(result["change_requests"][1]["sys_id"], "change456")

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_list_change_requests_empty_result(self, mock_get):
        """Test listing change requests with empty result."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the function
        params = {
            "limit": 10,
            "timeframe": "upcoming",
        }
        result = list_change_requests(self.auth_manager, self.server_config, params)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(len(result["change_requests"]), 0)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total"], 0)

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_list_change_requests_missing_result(self, mock_get):
        """Test listing change requests with missing result key."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No "result" key
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the function
        params = {
            "limit": 10,
            "timeframe": "upcoming",
        }
        result = list_change_requests(self.auth_manager, self.server_config, params)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(len(result["change_requests"]), 0)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total"], 0)

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_list_change_requests_error(self, mock_get):
        """Test listing change requests with error."""
        # Mock the response
        mock_get.side_effect = requests.exceptions.RequestException("Test error")

        # Call the function
        params = {
            "limit": 10,
            "timeframe": "upcoming",
        }
        result = list_change_requests(self.auth_manager, self.server_config, params)

        # Verify the result
        self.assertFalse(result["success"])
        self.assertIn("Error listing change requests", result["message"])

    @patch("servicenow_mcp.tools.change_tools.requests.get")
    def test_list_change_requests_with_filters(self, mock_get):
        """Test listing change requests with filters."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "change123",
                    "number": "CHG0010001",
                    "short_description": "Test Change",
                    "type": "normal",
                    "state": "open",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Call the function with filters
        params = {
            "limit": 10,
            "state": "open",
            "type": "normal",
            "category": "Hardware",
            "assignment_group": "IT Support",
            "timeframe": "upcoming",
            "query": "short_description=Test",
        }
        result = list_change_requests(self.auth_manager, self.server_config, params)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(len(result["change_requests"]), 1)
        
        # Verify that the correct query parameters were passed to the request
        args, kwargs = mock_get.call_args
        self.assertIn("params", kwargs)
        self.assertIn("sysparm_query", kwargs["params"])
        query = kwargs["params"]["sysparm_query"]
        
        # Check that all filters are in the query
        self.assertIn("state=open", query)
        self.assertIn("type=normal", query)
        self.assertIn("category=Hardware", query)
        self.assertIn("assignment_group=IT Support", query)
        self.assertIn("short_description=Test", query)
        # The timeframe filter adds a date comparison, which is harder to test exactly

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_create_change_request_with_swapped_parameters(self, mock_post):
        """Test creating a change request with swapped parameters (server_config used as auth_manager)."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "change123",
                "number": "CHG0010001",
                "short_description": "Test Change",
                "type": "normal",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Create a server_config with a get_headers method to simulate what might happen in Claude Desktop
        server_config_with_headers = MagicMock()
        server_config_with_headers.instance_url = "https://test.service-now.com"
        server_config_with_headers.get_headers.return_value = {"Authorization": "Basic dGVzdF91c2VyOnRlc3RfcGFzc3dvcmQ="}

        # Call the function with swapped parameters (server_config as auth_manager)
        params = {
            "short_description": "Test Change",
            "type": "normal",
            "risk": "low",
            "impact": "medium",
        }
        result = create_change_request(server_config_with_headers, self.auth_manager, params)

        # Verify the result
        self.assertFalse(result["success"])

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_create_change_request_with_serverconfig_no_get_headers(self, mock_post):
        """Test creating a change request with ServerConfig object that doesn't have get_headers method."""
        # This test simulates the exact error we're seeing in Claude Desktop
        
        # Create params for the change request
        params = {
            "short_description": "Test Change",
            "type": "normal",
            "risk": "low",
            "impact": "medium",
        }
        
        # Create a real ServerConfig object (which doesn't have get_headers method)
        # and a mock AuthManager object (which doesn't have instance_url)
        real_server_config = ServerConfig(
            instance_url="https://test.service-now.com",
            auth=self.auth_config,
        )
        
        mock_auth_manager = MagicMock()
        # Explicitly remove get_headers method to simulate the error
        if hasattr(mock_auth_manager, 'get_headers'):
            delattr(mock_auth_manager, 'get_headers')
        
        # Call the function with parameters that will cause the error
        result = create_change_request(real_server_config, mock_auth_manager, params)
        
        # The function should detect the issue and return an error message
        self.assertFalse(result["success"])
        self.assertIn("Cannot find get_headers method", result["message"])
        
        # Verify that the post method was never called
        mock_post.assert_not_called()

    @patch("servicenow_mcp.tools.change_tools.requests.post")
    def test_create_change_request_with_swapped_parameters_real(self, mock_post):
        """Test creating a change request with swapped parameters (auth_manager and server_config)."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "change123",
                "number": "CHG0010001",
                "short_description": "Test Change",
                "type": "normal",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Create params for the change request
        params = {
            "short_description": "Test Change",
            "type": "normal",
            "risk": "low",
            "impact": "medium",
        }
        
        # Call the function with swapped parameters (server_config as first parameter, auth_manager as second)
        result = create_change_request(self.server_config, self.auth_manager, params)
        
        # The function should still work correctly
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main() 