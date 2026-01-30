"""
Tests for the ServiceNow MCP server integration with catalog functionality.
"""

import unittest
from unittest.mock import patch

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestServerCatalog(unittest.TestCase):
    """Test cases for the server integration with catalog functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="admin", password="password"),
        )
        self.server_config = ServerConfig(
            instance_url="https://example.service-now.com",
            auth=self.auth_config,
        )

        # Create the server instance
        self.server = ServiceNowMCP(self.server_config)

    def test_catalog_tools_defined(self):
        """Test that catalog tools are defined in tool_definitions."""
        expected_tools = [
            "list_catalog_items",
            "get_catalog_item",
            "list_catalog_categories",
        ]
        for tool_name in expected_tools:
            self.assertIn(
                tool_name,
                self.server.tool_definitions,
                f"Expected tool '{tool_name}' to be in tool_definitions",
            )

    def test_catalog_tool_definitions_structure(self):
        """Test that catalog tool definitions have the expected structure."""
        for tool_name in ["list_catalog_items", "get_catalog_item", "list_catalog_categories"]:
            if tool_name in self.server.tool_definitions:
                definition = self.server.tool_definitions[tool_name]
                # Each definition is a tuple: (impl_func, params_model, return_annotation, description, serialization)
                self.assertEqual(len(definition), 5, f"Tool '{tool_name}' definition should have 5 elements")
                impl_func, params_model, _return_annotation, description, _serialization = definition
                self.assertTrue(callable(impl_func), f"Tool '{tool_name}' impl_func should be callable")
                self.assertIsNotNone(description, f"Tool '{tool_name}' should have a description")

    @patch.dict("os.environ", {"MCP_TOOL_PACKAGE": "full"})
    def test_catalog_tools_enabled_in_full_package(self):
        """Test that catalog tools are enabled in the full package."""
        server = ServiceNowMCP(self.server_config)
        expected_tools = [
            "list_catalog_items",
            "get_catalog_item",
            "list_catalog_categories",
        ]
        for tool_name in expected_tools:
            self.assertIn(
                tool_name,
                server.enabled_tool_names,
                f"Expected tool '{tool_name}' to be enabled in full package",
            )

    def test_server_initialization(self):
        """Test that the server initializes correctly with catalog tools available."""
        self.assertIsNotNone(self.server.mcp_server)
        self.assertIsNotNone(self.server.tool_definitions)
        self.assertGreater(len(self.server.tool_definitions), 0)


if __name__ == "__main__":
    unittest.main()
