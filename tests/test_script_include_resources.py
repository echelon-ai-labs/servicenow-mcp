"""
Tests for the script include resources.

This module contains tests for the script include resources in the ServiceNow MCP server.
"""

import json
import unittest
import requests
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.resources.script_includes import ScriptIncludeListParams, ScriptIncludeResource
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig


class TestScriptIncludeResource(unittest.IsolatedAsyncioTestCase):
    """Tests for the script include resource."""

    def setUp(self):
        """Set up test fixtures."""
        auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(
                username="test_user",
                password="test_password"
            )
        )
        self.server_config = ServerConfig(
            instance_url="https://test.service-now.com",
            auth=auth_config,
        )
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {"Authorization": "Bearer test"}
        self.script_include_resource = ScriptIncludeResource(self.server_config, self.auth_manager)

    @patch("servicenow_mcp.resources.script_includes.requests.get")
    async def test_list_script_includes(self, mock_get):
        """Test listing script includes."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "result": [
                {
                    "sys_id": "123",
                    "name": "TestScriptInclude",
                    "script": "var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
                    "description": "Test Script Include",
                    "api_name": "global.TestScriptInclude",
                    "client_callable": "true",
                    "active": "true",
                    "access": "public",
                    "sys_created_on": "2023-01-01 00:00:00",
                    "sys_updated_on": "2023-01-02 00:00:00",
                    "sys_created_by": {"display_value": "admin"},
                    "sys_updated_by": {"display_value": "admin"}
                }
            ]
        })
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the method
        params = ScriptIncludeListParams(
            limit=10,
            offset=0,
            active=True,
            client_callable=True,
            query="Test"
        )
        result = await self.script_include_resource.list_script_includes(params)
        result_json = json.loads(result)

        # Verify the result
        self.assertIn("result", result_json)
        self.assertEqual(1, len(result_json["result"]))
        self.assertEqual("123", result_json["result"][0]["sys_id"])
        self.assertEqual("TestScriptInclude", result_json["result"][0]["name"])
        self.assertEqual("true", result_json["result"][0]["client_callable"])
        self.assertEqual("true", result_json["result"][0]["active"])

        # Verify the request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include", args[0])
        self.assertEqual({"Authorization": "Bearer test"}, kwargs["headers"])
        self.assertEqual(10, kwargs["params"]["sysparm_limit"])
        self.assertEqual(0, kwargs["params"]["sysparm_offset"])
        self.assertEqual("active=true^client_callable=true^nameLIKETest", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.resources.script_includes.requests.get")
    async def test_get_script_include(self, mock_get):
        """Test getting a script include."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "result": {
                "sys_id": "123",
                "name": "TestScriptInclude",
                "script": "var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
                "description": "Test Script Include",
                "api_name": "global.TestScriptInclude",
                "client_callable": "true",
                "active": "true",
                "access": "public",
                "sys_created_on": "2023-01-01 00:00:00",
                "sys_updated_on": "2023-01-02 00:00:00",
                "sys_created_by": {"display_value": "admin"},
                "sys_updated_by": {"display_value": "admin"}
            }
        })
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the method
        result = await self.script_include_resource.get_script_include("123")
        result_json = json.loads(result)

        # Verify the result
        self.assertIn("result", result_json)
        self.assertEqual("123", result_json["result"]["sys_id"])
        self.assertEqual("TestScriptInclude", result_json["result"]["name"])
        self.assertEqual("true", result_json["result"]["client_callable"])
        self.assertEqual("true", result_json["result"]["active"])

        # Verify the request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include", args[0])
        self.assertEqual({"Authorization": "Bearer test"}, kwargs["headers"])
        self.assertEqual("name=123", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.resources.script_includes.requests.get")
    async def test_get_script_include_by_sys_id(self, mock_get):
        """Test getting a script include by sys_id."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "result": {
                "sys_id": "123",
                "name": "TestScriptInclude",
                "script": "var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
                "description": "Test Script Include",
                "api_name": "global.TestScriptInclude",
                "client_callable": "true",
                "active": "true",
                "access": "public",
                "sys_created_on": "2023-01-01 00:00:00",
                "sys_updated_on": "2023-01-02 00:00:00",
                "sys_created_by": {"display_value": "admin"},
                "sys_updated_by": {"display_value": "admin"}
            }
        })
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the method
        result = await self.script_include_resource.get_script_include("sys_id:123")
        result_json = json.loads(result)

        # Verify the result
        self.assertIn("result", result_json)
        self.assertEqual("123", result_json["result"]["sys_id"])
        self.assertEqual("TestScriptInclude", result_json["result"]["name"])

        # Verify the request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include/123", args[0])
        self.assertEqual({"Authorization": "Bearer test"}, kwargs["headers"])

    @patch("servicenow_mcp.resources.script_includes.requests.get")
    async def test_list_script_includes_error(self, mock_get):
        """Test listing script includes with an error."""
        # Mock response
        mock_get.side_effect = requests.RequestException("Test error")

        # Call the method
        params = ScriptIncludeListParams()
        result = await self.script_include_resource.list_script_includes(params)
        result_json = json.loads(result)

        # Verify the result
        self.assertIn("error", result_json)
        self.assertIn("Error listing script includes", result_json["error"])

    @patch("servicenow_mcp.resources.script_includes.requests.get")
    async def test_get_script_include_error(self, mock_get):
        """Test getting a script include with an error."""
        # Mock response
        mock_get.side_effect = requests.RequestException("Test error")

        # Call the method
        result = await self.script_include_resource.get_script_include("123")
        result_json = json.loads(result)

        # Verify the result
        self.assertIn("error", result_json)
        self.assertIn("Error getting script include", result_json["error"])


class TestScriptIncludeListParams(unittest.TestCase):
    """Tests for the script include list parameters."""

    def test_script_include_list_params(self):
        """Test script include list parameters."""
        params = ScriptIncludeListParams(
            limit=20,
            offset=10,
            active=True,
            client_callable=False,
            query="Test"
        )
        self.assertEqual(20, params.limit)
        self.assertEqual(10, params.offset)
        self.assertTrue(params.active)
        self.assertFalse(params.client_callable)
        self.assertEqual("Test", params.query)

    def test_script_include_list_params_defaults(self):
        """Test script include list parameters defaults."""
        params = ScriptIncludeListParams()
        self.assertEqual(10, params.limit)
        self.assertEqual(0, params.offset)
        self.assertIsNone(params.active)
        self.assertIsNone(params.client_callable)
        self.assertIsNone(params.query) 