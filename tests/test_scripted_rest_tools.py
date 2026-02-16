"""
Tests for the scripted REST API tools.

This module contains tests for the scripted REST API tools in the ServiceNow MCP server.
"""

import unittest
import requests
from unittest.mock import MagicMock, patch

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.scripted_rest_tools import (
    CreateScriptedRestApiParams,
    CreateScriptedRestResourceParams,
    ScriptedRestResponse,
    create_scripted_rest_api,
    create_scripted_rest_resource,
)
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig


class TestScriptedRestTools(unittest.TestCase):
    """Tests for the scripted REST API tools."""

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

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_api(self, mock_post):
        """Test creating a Scripted REST API service."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "abc123",
                "name": "NowLLM Chat API",
            }
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        params = CreateScriptedRestApiParams(
            name="NowLLM Chat API",
            api_id="nowllm_chat",
            short_description="REST API for NowLLM chat integration",
            is_active=True,
        )
        result = create_scripted_rest_api(self.server_config, self.auth_manager, params)

        self.assertTrue(result.success)
        self.assertEqual("abc123", result.sys_id)
        self.assertEqual("NowLLM Chat API", result.name)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(
            f"{self.server_config.instance_url}/api/now/table/sys_ws_definition", args[0]
        )
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])
        self.assertEqual("NowLLM Chat API", kwargs["json"]["name"])
        self.assertEqual("nowllm_chat", kwargs["json"]["service_id"])
        self.assertEqual("true", kwargs["json"]["is_active"])
        self.assertEqual("REST API for NowLLM chat integration", kwargs["json"]["short_description"])

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_api_minimal(self, mock_post):
        """Test creating a Scripted REST API service with only required fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "abc123",
                "name": "My API",
            }
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        params = CreateScriptedRestApiParams(name="My API")
        result = create_scripted_rest_api(self.server_config, self.auth_manager, params)

        self.assertTrue(result.success)
        self.assertEqual("abc123", result.sys_id)

        args, kwargs = mock_post.call_args
        self.assertNotIn("service_id", kwargs["json"])
        self.assertNotIn("short_description", kwargs["json"])
        self.assertEqual("true", kwargs["json"]["is_active"])

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_api_no_result(self, mock_post):
        """Test creating a Scripted REST API service when response has no result."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        params = CreateScriptedRestApiParams(name="My API")
        result = create_scripted_rest_api(self.server_config, self.auth_manager, params)

        self.assertFalse(result.success)
        self.assertIn("Failed to create", result.message)

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_api_error(self, mock_post):
        """Test creating a Scripted REST API service with an error."""
        mock_post.side_effect = requests.RequestException("Connection error")

        params = CreateScriptedRestApiParams(name="My API")
        result = create_scripted_rest_api(self.server_config, self.auth_manager, params)

        self.assertFalse(result.success)
        self.assertIn("Error creating Scripted REST API service", result.message)
        self.assertIn("Connection error", result.message)

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_resource(self, mock_post):
        """Test creating a Scripted REST API resource."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "def456",
                "name": "Generate",
            }
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        params = CreateScriptedRestResourceParams(
            web_service_definition="abc123",
            name="Generate",
            http_method="POST",
            relative_path="/generate",
            operation_script="(function process(request, response) { response.setStatus(200); })(request, response);",
            short_description="Generate chat response",
            active=True,
        )
        result = create_scripted_rest_resource(self.server_config, self.auth_manager, params)

        self.assertTrue(result.success)
        self.assertEqual("def456", result.sys_id)
        self.assertEqual("Generate", result.name)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(
            f"{self.server_config.instance_url}/api/now/table/sys_ws_operation", args[0]
        )
        self.assertEqual(self.auth_manager.get_headers(), kwargs["headers"])
        self.assertEqual("abc123", kwargs["json"]["web_service_definition"])
        self.assertEqual("Generate", kwargs["json"]["name"])
        self.assertEqual("POST", kwargs["json"]["http_method"])
        self.assertEqual("/generate", kwargs["json"]["relative_path"])
        self.assertEqual("true", kwargs["json"]["active"])
        self.assertEqual("Generate chat response", kwargs["json"]["short_description"])

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_resource_minimal(self, mock_post):
        """Test creating a Scripted REST API resource with only required fields."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "def456",
                "name": "Get Items",
            }
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        params = CreateScriptedRestResourceParams(
            web_service_definition="abc123",
            name="Get Items",
            http_method="get",
            relative_path="/items",
            operation_script="(function process(request, response) { })(request, response);",
        )
        result = create_scripted_rest_resource(self.server_config, self.auth_manager, params)

        self.assertTrue(result.success)

        args, kwargs = mock_post.call_args
        self.assertEqual("GET", kwargs["json"]["http_method"])
        self.assertNotIn("short_description", kwargs["json"])
        self.assertEqual("true", kwargs["json"]["active"])

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_resource_no_result(self, mock_post):
        """Test creating a Scripted REST API resource when response has no result."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        params = CreateScriptedRestResourceParams(
            web_service_definition="abc123",
            name="Generate",
            http_method="POST",
            relative_path="/generate",
            operation_script="(function process(request, response) { })(request, response);",
        )
        result = create_scripted_rest_resource(self.server_config, self.auth_manager, params)

        self.assertFalse(result.success)
        self.assertIn("Failed to create", result.message)

    @patch("servicenow_mcp.tools.scripted_rest_tools.requests.post")
    def test_create_scripted_rest_resource_error(self, mock_post):
        """Test creating a Scripted REST API resource with an error."""
        mock_post.side_effect = requests.RequestException("Timeout")

        params = CreateScriptedRestResourceParams(
            web_service_definition="abc123",
            name="Generate",
            http_method="POST",
            relative_path="/generate",
            operation_script="(function process(request, response) { })(request, response);",
        )
        result = create_scripted_rest_resource(self.server_config, self.auth_manager, params)

        self.assertFalse(result.success)
        self.assertIn("Error creating Scripted REST API resource", result.message)
        self.assertIn("Timeout", result.message)


class TestScriptedRestParams(unittest.TestCase):
    """Tests for the scripted REST API parameters."""

    def test_create_scripted_rest_api_params(self):
        """Test CreateScriptedRestApiParams model."""
        params = CreateScriptedRestApiParams(
            name="NowLLM Chat API",
            api_id="nowllm_chat",
            short_description="Chat API",
            is_active=False,
        )
        self.assertEqual("NowLLM Chat API", params.name)
        self.assertEqual("nowllm_chat", params.api_id)
        self.assertEqual("Chat API", params.short_description)
        self.assertFalse(params.is_active)

    def test_create_scripted_rest_api_params_defaults(self):
        """Test CreateScriptedRestApiParams defaults."""
        params = CreateScriptedRestApiParams(name="My API")
        self.assertEqual("My API", params.name)
        self.assertIsNone(params.api_id)
        self.assertIsNone(params.short_description)
        self.assertTrue(params.is_active)

    def test_create_scripted_rest_resource_params(self):
        """Test CreateScriptedRestResourceParams model."""
        params = CreateScriptedRestResourceParams(
            web_service_definition="abc123",
            name="Generate",
            http_method="POST",
            relative_path="/generate",
            operation_script="// script",
            short_description="Generate endpoint",
            active=False,
        )
        self.assertEqual("abc123", params.web_service_definition)
        self.assertEqual("Generate", params.name)
        self.assertEqual("POST", params.http_method)
        self.assertEqual("/generate", params.relative_path)
        self.assertEqual("// script", params.operation_script)
        self.assertEqual("Generate endpoint", params.short_description)
        self.assertFalse(params.active)

    def test_create_scripted_rest_resource_params_defaults(self):
        """Test CreateScriptedRestResourceParams defaults."""
        params = CreateScriptedRestResourceParams(
            web_service_definition="abc123",
            name="Generate",
            http_method="POST",
            relative_path="/generate",
            operation_script="// script",
        )
        self.assertIsNone(params.short_description)
        self.assertTrue(params.active)

    def test_scripted_rest_response(self):
        """Test ScriptedRestResponse model."""
        response = ScriptedRestResponse(
            success=True,
            message="Created",
            sys_id="abc123",
            name="My API",
        )
        self.assertTrue(response.success)
        self.assertEqual("Created", response.message)
        self.assertEqual("abc123", response.sys_id)
        self.assertEqual("My API", response.name)

    def test_scripted_rest_response_minimal(self):
        """Test ScriptedRestResponse with only required fields."""
        response = ScriptedRestResponse(
            success=False,
            message="Failed",
        )
        self.assertFalse(response.success)
        self.assertEqual("Failed", response.message)
        self.assertIsNone(response.sys_id)
        self.assertIsNone(response.name)
