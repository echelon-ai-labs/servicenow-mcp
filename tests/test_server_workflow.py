"""
Tests for the ServiceNow MCP server workflow management integration.
"""

import os
import unittest

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestServerWorkflow(unittest.TestCase):
    """Tests for the ServiceNow MCP server workflow management integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Set environment variable to load all tools
        os.environ["MCP_TOOL_PACKAGE"] = "full"
        
        self.auth_config = AuthConfig(
            type=AuthType.BASIC,
            basic=BasicAuthConfig(username="test_user", password="test_password"),
        )
        self.server_config = ServerConfig(
            instance_url="https://test.service-now.com",
            auth=self.auth_config,
        )
        
        # Create the server instance directly (no mocking needed)
        self.server = ServiceNowMCP(self.server_config)

    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up environment variable
        if "MCP_TOOL_PACKAGE" in os.environ:
            del os.environ["MCP_TOOL_PACKAGE"]

    def test_workflow_tools_in_tool_definitions(self):
        """Test that workflow tools are included in tool definitions."""
        # Check for workflow tool registrations
        workflow_tools = [
            "list_workflows",
            "get_workflow_details",
            "list_workflow_versions",
            "get_workflow_activities",
            "create_workflow",
            "update_workflow",
            "activate_workflow",
            "deactivate_workflow",
            "add_workflow_activity",
            "update_workflow_activity",
            "delete_workflow_activity",
            "reorder_workflow_activities",
        ]
        
        # Check that all workflow tools are in the tool definitions
        for tool_name in workflow_tools:
            self.assertIn(
                tool_name,
                self.server.tool_definitions,
                f"Expected {tool_name} to be in tool definitions",
            )

    def test_workflow_tools_enabled_in_full_package(self):
        """Test that workflow tools are enabled in the full package."""
        # Check for workflow tool registrations
        workflow_tools = [
            "list_workflows",
            "get_workflow_details",
            "list_workflow_versions",
            "get_workflow_activities",
            "create_workflow",
            "update_workflow",
            "activate_workflow",
            "deactivate_workflow",
            "add_workflow_activity",
            "update_workflow_activity",
            "delete_workflow_activity",
            "reorder_workflow_activities",
        ]
        
        # Check that all workflow tools are enabled
        for tool_name in workflow_tools:
            self.assertIn(
                tool_name,
                self.server.enabled_tool_names,
                f"Expected {tool_name} to be enabled in full package",
            )


if __name__ == "__main__":
    unittest.main() 