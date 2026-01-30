"""
Tests for the ServiceNow MCP server workflow management integration.
"""

import unittest
from unittest.mock import patch

from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestServerWorkflow(unittest.TestCase):
    """Tests for the ServiceNow MCP server workflow management integration."""

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

        # Create the server instance
        self.server = ServiceNowMCP(self.server_config)

    def test_workflow_tools_defined(self):
        """Test that workflow tools are defined in tool_definitions."""
        expected_tools = [
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
        for tool_name in expected_tools:
            self.assertIn(
                tool_name,
                self.server.tool_definitions,
                f"Expected workflow tool '{tool_name}' to be in tool_definitions",
            )

    @patch.dict("os.environ", {"MCP_TOOL_PACKAGE": "full"})
    def test_workflow_tools_enabled_in_full_package(self):
        """Test that workflow tools are enabled in the full package."""
        server = ServiceNowMCP(self.server_config)
        expected_tools = [
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
        for tool_name in expected_tools:
            self.assertIn(
                tool_name,
                server.enabled_tool_names,
                f"Expected workflow tool '{tool_name}' to be enabled in full package",
            )


if __name__ == "__main__":
    unittest.main()
