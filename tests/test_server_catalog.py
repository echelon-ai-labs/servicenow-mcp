"""
Tests for the ServiceNow MCP server integration with catalog functionality.
"""

import os
import unittest
from unittest.mock import patch

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestServerCatalog(unittest.IsolatedAsyncioTestCase):
    """Test cases for the server integration with catalog functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Set environment variable to load catalog tools
        os.environ["MCP_TOOL_PACKAGE"] = "full"
        
        # Create proper configuration objects
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test_user", password="test_password"),
        )
        self.server_config = ServerConfig(
            instance_url="https://test.service-now.com",
            auth=self.auth_config,
        )

        # Create the server instance
        self.server = ServiceNowMCP(self.server_config)

    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up environment variable
        if "MCP_TOOL_PACKAGE" in os.environ:
            del os.environ["MCP_TOOL_PACKAGE"]

    def test_catalog_tools_in_tool_definitions(self):
        """Test that catalog tools are included in tool definitions."""
        # Check that catalog tools are in the tool definitions
        catalog_tools = [
            "list_catalog_items",
            "get_catalog_item",
            "list_catalog_categories",
            "create_catalog_category",
            "update_catalog_category",
            "move_catalog_items",
        ]
        
        for tool_name in catalog_tools:
            self.assertIn(
                tool_name,
                self.server.tool_definitions,
                f"Expected {tool_name} to be in tool definitions",
            )

    def test_catalog_tools_enabled_in_full_package(self):
        """Test that catalog tools are enabled in the full package."""
        # Check that catalog tools are enabled
        catalog_tools = [
            "list_catalog_items",
            "get_catalog_item",
            "list_catalog_categories",
        ]
        
        for tool_name in catalog_tools:
            self.assertIn(
                tool_name,
                self.server.enabled_tool_names,
                f"Expected {tool_name} to be enabled in full package",
            )

    async def test_list_catalog_tools(self):
        """Test listing catalog tools via the MCP server."""
        # Get the list of tools
        tools = await self.server._list_tools_impl()
        
        # Check that catalog tools are in the list
        tool_names = [tool.name for tool in tools]
        
        self.assertIn("list_catalog_items", tool_names)
        self.assertIn("get_catalog_item", tool_names)
        self.assertIn("list_catalog_categories", tool_names)

    @patch("servicenow_mcp.tools.catalog_tools.requests.get")
    async def test_call_list_catalog_items(self, mock_get):
        """Test calling the list_catalog_items tool."""
        # Mock the HTTP response
        mock_response = patch.object(mock_get, "return_value")
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": [
                {
                    "sys_id": "item1",
                    "name": "Laptop",
                    "short_description": "Standard laptop",
                    "category": "hardware",
                    "price": "1000",
                    "picture": "",
                    "active": "true",
                    "order": "100",
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None

        # Call the tool
        result = await self.server._call_tool_impl(
            "list_catalog_items",
            {"category": None, "limit": 10},
        )

        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("item1", result[0].text)
        self.assertIn("Laptop", result[0].text)

    @patch("servicenow_mcp.tools.catalog_tools.requests.get")
    async def test_call_get_catalog_item(self, mock_get):
        """Test calling the get_catalog_item tool."""
        # Mock the HTTP response for the main item
        def side_effect(url, *args, **kwargs):
            from unittest.mock import MagicMock
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.raise_for_status = MagicMock()
            
            if "sc_cat_item" in url and "item_option_new" not in url:
                mock_response_obj.json.return_value = {
                    "result": {
                        "sys_id": "item1",
                        "name": "Laptop",
                        "short_description": "Standard laptop",
                        "description": "A standard laptop",
                        "category": "hardware",
                        "price": "1000",
                        "picture": "",
                        "active": "true",
                        "order": "100",
                        "delivery_time": "3-5 days",
                        "availability": "in stock",
                    }
                }
            else:  # item_option_new for variables
                mock_response_obj.json.return_value = {"result": []}
            
            return mock_response_obj
        
        mock_get.side_effect = side_effect

        # Call the tool
        result = await self.server._call_tool_impl(
            "get_catalog_item",
            {"item_id": "item1"},
        )

        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("item1", result[0].text)
        self.assertIn("Laptop", result[0].text)

    @patch("servicenow_mcp.tools.catalog_tools.requests.get")
    async def test_call_list_catalog_categories(self, mock_get):
        """Test calling the list_catalog_categories tool."""
        # Mock the HTTP response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "result": [
                {
                    "sys_id": "cat1",
                    "title": "Hardware",
                    "description": "Hardware category",
                    "parent": "",
                    "icon": "",
                    "active": "true",
                    "order": "100",
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None

        # Call the tool
        result = await self.server._call_tool_impl(
            "list_catalog_categories",
            {"parent_category": None, "limit": 10},
        )

        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("cat1", result[0].text)
        self.assertIn("Hardware", result[0].text)


if __name__ == "__main__":
    unittest.main()
