"""
Tests for the script include tools.

This module contains tests for the script include tools in the ServiceNow MCP server.
"""

import unittest
import requests
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.script_include_tools import (
    ListScriptIncludesParams,
    GetScriptIncludeParams,
    CreateScriptIncludeParams,
    UpdateScriptIncludeParams,
    DeleteScriptIncludeParams,
    ScriptIncludeResponse,
    list_script_includes,
    get_script_include,
    create_script_include,
    update_script_include,
    delete_script_include,
)
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig


class TestScriptIncludeTools(unittest.TestCase):
    """Tests for the script include tools."""

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
        self.auth_manager.get_headers.return_value = {
            "Authorization": "Bearer test",
            "Content-Type": "application/json",
        }

    @patch("servicenow_mcp.tools.script_include_tools.requests.get")
    def test_list_script_includes(self, mock_get):
        """Test listing script includes."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
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
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the method
        params = ListScriptIncludesParams(
            limit=10,
            offset=0,
            active=True,
            client_callable=True,
            query="Test"
        )
        result = list_script_includes(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(1, len(result["script_includes"]))
        self.assertEqual("123", result["script_includes"][0]["sys_id"])
        self.assertEqual("TestScriptInclude", result["script_includes"][0]["name"])
        self.assertTrue(result["script_includes"][0]["client_callable"])
        self.assertTrue(result["script_includes"][0]["active"])

        # Verify the request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include", args[0])
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])
        self.assertEqual(10, kwargs["params"]["sysparm_limit"])
        self.assertEqual(0, kwargs["params"]["sysparm_offset"])
        self.assertEqual("active=true^client_callable=true^nameLIKETest", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.script_include_tools.requests.get")
    def test_get_script_include(self, mock_get):
        """Test getting a script include."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
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
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the method
        params = GetScriptIncludeParams(script_include_id="123")
        result = get_script_include(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual("123", result["script_include"]["sys_id"])
        self.assertEqual("TestScriptInclude", result["script_include"]["name"])
        self.assertTrue(result["script_include"]["client_callable"])
        self.assertTrue(result["script_include"]["active"])

        # Verify the request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include", args[0])
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])
        self.assertEqual("name=123", kwargs["params"]["sysparm_query"])

    @patch("servicenow_mcp.tools.script_include_tools.requests.post")
    def test_create_script_include(self, mock_post):
        """Test creating a script include."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "123",
                "name": "TestScriptInclude",
            }
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        # Call the method
        params = CreateScriptIncludeParams(
            name="TestScriptInclude",
            script="var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
            description="Test Script Include",
            api_name="global.TestScriptInclude",
            client_callable=True,
            active=True,
            access="public"
        )
        result = create_script_include(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertTrue(result.success)
        self.assertEqual("123", result.script_include_id)
        self.assertEqual("TestScriptInclude", result.script_include_name)

        # Verify the request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include", args[0])
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])
        self.assertEqual("TestScriptInclude", kwargs["json"]["name"])
        self.assertEqual("true", kwargs["json"]["client_callable"])
        self.assertEqual("true", kwargs["json"]["active"])
        self.assertEqual("public", kwargs["json"]["access"])

    @patch("servicenow_mcp.tools.script_include_tools.get_script_include")
    @patch("servicenow_mcp.tools.script_include_tools.requests.patch")
    def test_update_script_include(self, mock_patch, mock_get_script_include):
        """Test updating a script include."""
        # Mock get_script_include response
        mock_get_script_include.return_value = {
            "success": True,
            "message": "Found script include: TestScriptInclude",
            "script_include": {
                "sys_id": "123",
                "name": "TestScriptInclude",
                "script": "var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
                "description": "Test Script Include",
                "api_name": "global.TestScriptInclude",
                "client_callable": True,
                "active": True,
                "access": "public",
            }
        }

        # Mock patch response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "123",
                "name": "TestScriptInclude",
            }
        }
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        # Call the method
        params = UpdateScriptIncludeParams(
            script_include_id="123",
            script="var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n        // Updated\n    },\n\n    type: 'TestScriptInclude'\n};",
            description="Updated Test Script Include",
            client_callable=False,
        )
        result = update_script_include(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertTrue(result.success)
        self.assertEqual("123", result.script_include_id)
        self.assertEqual("TestScriptInclude", result.script_include_name)

        # Verify the request
        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include/123", args[0])
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])
        self.assertEqual("Updated Test Script Include", kwargs["json"]["description"])
        self.assertEqual("false", kwargs["json"]["client_callable"])

    @patch("servicenow_mcp.tools.script_include_tools.get_script_include")
    @patch("servicenow_mcp.tools.script_include_tools.requests.delete")
    def test_delete_script_include(self, mock_delete, mock_get_script_include):
        """Test deleting a script include."""
        # Mock get_script_include response
        mock_get_script_include.return_value = {
            "success": True,
            "message": "Found script include: TestScriptInclude",
            "script_include": {
                "sys_id": "123",
                "name": "TestScriptInclude",
            }
        }

        # Mock delete response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        # Call the method
        params = DeleteScriptIncludeParams(script_include_id="123")
        result = delete_script_include(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertTrue(result.success)
        self.assertEqual("123", result.script_include_id)
        self.assertEqual("TestScriptInclude", result.script_include_name)

        # Verify the request
        mock_delete.assert_called_once()
        args, kwargs = mock_delete.call_args
        self.assertEqual(f"{self.server_config.instance_url}/api/now/table/sys_script_include/123", args[0])
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])

    @patch("servicenow_mcp.tools.script_include_tools.requests.get")
    def test_list_script_includes_error(self, mock_get):
        """Test listing script includes with an error."""
        # Mock response
        mock_get.side_effect = requests.RequestException("Test error")

        # Call the method
        params = ListScriptIncludesParams()
        result = list_script_includes(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertFalse(result["success"])
        self.assertIn("Error listing script includes", result["message"])

    @patch("servicenow_mcp.tools.script_include_tools.requests.get")
    def test_get_script_include_error(self, mock_get):
        """Test getting a script include with an error."""
        # Mock response
        mock_get.side_effect = requests.RequestException("Test error")

        # Call the method
        params = GetScriptIncludeParams(script_include_id="123")
        result = get_script_include(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertFalse(result["success"])
        self.assertIn("Error getting script include", result["message"])

    @patch("servicenow_mcp.tools.script_include_tools.requests.post")
    def test_create_script_include_error(self, mock_post):
        """Test creating a script include with an error."""
        # Mock response
        mock_post.side_effect = requests.RequestException("Test error")

        # Call the method
        params = CreateScriptIncludeParams(
            name="TestScriptInclude",
            script="var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
        )
        result = create_script_include(self.server_config, self.auth_manager, params)

        # Verify the result
        self.assertFalse(result.success)
        self.assertIn("Error creating script include", result.message)


class TestScriptIncludeParams(unittest.TestCase):
    """Tests for the script include parameters."""

    def test_list_script_includes_params(self):
        """Test list script includes parameters."""
        params = ListScriptIncludesParams(
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

    def test_get_script_include_params(self):
        """Test get script include parameters."""
        params = GetScriptIncludeParams(script_include_id="123")
        self.assertEqual("123", params.script_include_id)

    def test_create_script_include_params(self):
        """Test create script include parameters."""
        params = CreateScriptIncludeParams(
            name="TestScriptInclude",
            script="var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n    },\n\n    type: 'TestScriptInclude'\n};",
            description="Test Script Include",
            api_name="global.TestScriptInclude",
            client_callable=True,
            active=True,
            access="public"
        )
        self.assertEqual("TestScriptInclude", params.name)
        self.assertTrue(params.client_callable)
        self.assertTrue(params.active)
        self.assertEqual("public", params.access)

    def test_update_script_include_params(self):
        """Test update script include parameters."""
        params = UpdateScriptIncludeParams(
            script_include_id="123",
            script="var TestScriptInclude = Class.create();\nTestScriptInclude.prototype = {\n    initialize: function() {\n        // Updated\n    },\n\n    type: 'TestScriptInclude'\n};",
            description="Updated Test Script Include",
            client_callable=False,
        )
        self.assertEqual("123", params.script_include_id)
        self.assertEqual("Updated Test Script Include", params.description)
        self.assertFalse(params.client_callable)

    def test_delete_script_include_params(self):
        """Test delete script include parameters."""
        params = DeleteScriptIncludeParams(script_include_id="123")
        self.assertEqual("123", params.script_include_id)

    def test_script_include_response(self):
        """Test script include response."""
        response = ScriptIncludeResponse(
            success=True,
            message="Test message",
            script_include_id="123",
            script_include_name="TestScriptInclude"
        )
        self.assertTrue(response.success)
        self.assertEqual("Test message", response.message)
        self.assertEqual("123", response.script_include_id)
        self.assertEqual("TestScriptInclude", response.script_include_name) 