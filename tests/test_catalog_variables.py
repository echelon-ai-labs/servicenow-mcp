"""
Tests for the catalog item variables tools.
"""

import unittest
from unittest.mock import MagicMock, patch
import requests

from servicenow_mcp.tools.catalog_variables import (
    CreateCatalogItemVariableParams,
    ListCatalogItemVariablesParams,
    UpdateCatalogItemVariableParams,
    create_catalog_item_variable,
    list_catalog_item_variables,
    update_catalog_item_variable,
)
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig


class TestCatalogVariablesTools(unittest.TestCase):
    """
    Test the catalog item variables tools.
    """

    def setUp(self):
        """Set up the test environment."""
        self.config = ServerConfig(
            instance_url="https://test.service-now.com",
            timeout=10,
            auth=AuthConfig(
                type=AuthType.BASIC,
                basic=BasicAuthConfig(
                    username="test_user",
                    password="test_password"
                )
            ),
        )
        self.auth_manager = MagicMock()
        self.auth_manager.get_headers.return_value = {"Content-Type": "application/json"}

    @patch("requests.post")
    def test_create_catalog_item_variable(self, mock_post):
        """Test create_catalog_item_variable function."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "abc123",
                "name": "test_variable",
                "type": "string",
                "question_text": "Test Variable",
                "mandatory": "false",
            }
        }
        mock_post.return_value = mock_response

        # Create test params
        params = CreateCatalogItemVariableParams(
            catalog_item_id="item123",
            name="test_variable",
            type="string",
            label="Test Variable",
            mandatory=False,
        )

        # Call function
        result = create_catalog_item_variable(self.config, self.auth_manager, params)

        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.variable_id, "abc123")
        self.assertIsNotNone(result.details)

        # Verify mock was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(
            call_args[0][0], f"{self.config.instance_url}/api/now/table/item_option_new"
        )
        self.assertEqual(call_args[1]["json"]["cat_item"], "item123")
        self.assertEqual(call_args[1]["json"]["name"], "test_variable")
        self.assertEqual(call_args[1]["json"]["type"], "string")
        self.assertEqual(call_args[1]["json"]["question_text"], "Test Variable")
        self.assertEqual(call_args[1]["json"]["mandatory"], "false")

    @patch("requests.post")
    def test_create_catalog_item_variable_with_optional_params(self, mock_post):
        """Test create_catalog_item_variable function with optional parameters."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "abc123",
                "name": "test_variable",
                "type": "reference",
                "question_text": "Test Reference",
                "mandatory": "true",
                "reference": "sys_user",
                "reference_qual": "active=true",
                "help_text": "Select a user",
                "default_value": "admin",
                "description": "Reference to a user",
                "order": 100,
            }
        }
        mock_post.return_value = mock_response

        # Create test params with optional fields
        params = CreateCatalogItemVariableParams(
            catalog_item_id="item123",
            name="test_variable",
            type="reference",
            label="Test Reference",
            mandatory=True,
            help_text="Select a user",
            default_value="admin",
            description="Reference to a user",
            order=100,
            reference_table="sys_user",
            reference_qualifier="active=true",
        )

        # Call function
        result = create_catalog_item_variable(self.config, self.auth_manager, params)

        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.variable_id, "abc123")

        # Verify mock was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["json"]["reference"], "sys_user")
        self.assertEqual(call_args[1]["json"]["reference_qual"], "active=true")
        self.assertEqual(call_args[1]["json"]["help_text"], "Select a user")
        self.assertEqual(call_args[1]["json"]["default_value"], "admin")
        self.assertEqual(call_args[1]["json"]["description"], "Reference to a user")
        self.assertEqual(call_args[1]["json"]["order"], 100)

    @patch("requests.post")
    def test_create_catalog_item_variable_error(self, mock_post):
        """Test create_catalog_item_variable function with error."""
        # Configure mock to raise exception
        mock_post.side_effect = requests.RequestException("Test error")

        # Create test params
        params = CreateCatalogItemVariableParams(
            catalog_item_id="item123",
            name="test_variable",
            type="string",
            label="Test Variable",
        )

        # Call function
        result = create_catalog_item_variable(self.config, self.auth_manager, params)

        # Verify result
        self.assertFalse(result.success)
        self.assertTrue("failed" in result.message.lower())

    @patch("requests.get")
    def test_list_catalog_item_variables(self, mock_get):
        """Test list_catalog_item_variables function."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "var1",
                    "name": "variable1",
                    "type": "string",
                    "question_text": "Variable 1",
                    "order": 100,
                    "mandatory": "true",
                },
                {
                    "sys_id": "var2",
                    "name": "variable2",
                    "type": "integer",
                    "question_text": "Variable 2",
                    "order": 200,
                    "mandatory": "false",
                },
            ]
        }
        mock_get.return_value = mock_response

        # Create test params
        params = ListCatalogItemVariablesParams(
            catalog_item_id="item123",
            include_details=True,
        )

        # Call function
        result = list_catalog_item_variables(self.config, self.auth_manager, params)

        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.count, 2)
        self.assertEqual(len(result.variables), 2)
        self.assertEqual(result.variables[0]["sys_id"], "var1")
        self.assertEqual(result.variables[1]["sys_id"], "var2")

        # Verify mock was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(
            call_args[0][0], f"{self.config.instance_url}/api/now/table/item_option_new"
        )
        self.assertEqual(
            call_args[1]["params"]["sysparm_query"], "cat_item=item123^ORDERBYorder"
        )
        self.assertEqual(call_args[1]["params"]["sysparm_display_value"], "true")
        self.assertEqual(call_args[1]["params"]["sysparm_exclude_reference_link"], "false")

    @patch("requests.get")
    def test_list_catalog_item_variables_with_pagination(self, mock_get):
        """Test list_catalog_item_variables function with pagination parameters."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": [{"sys_id": "var1"}]}
        mock_get.return_value = mock_response

        # Create test params with pagination
        params = ListCatalogItemVariablesParams(
            catalog_item_id="item123",
            include_details=False,
            limit=10,
            offset=20,
        )

        # Call function
        result = list_catalog_item_variables(self.config, self.auth_manager, params)

        # Verify result
        self.assertTrue(result.success)

        # Verify mock was called correctly with pagination
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]["params"]["sysparm_limit"], 10)
        self.assertEqual(call_args[1]["params"]["sysparm_offset"], 20)
        self.assertEqual(
            call_args[1]["params"]["sysparm_fields"],
            "sys_id,name,type,question_text,order,mandatory",
        )

    @patch("requests.get")
    def test_list_catalog_item_variables_error(self, mock_get):
        """Test list_catalog_item_variables function with error."""
        # Configure mock to raise exception
        mock_get.side_effect = requests.RequestException("Test error")

        # Create test params
        params = ListCatalogItemVariablesParams(
            catalog_item_id="item123",
        )

        # Call function
        result = list_catalog_item_variables(self.config, self.auth_manager, params)

        # Verify result
        self.assertFalse(result.success)
        self.assertTrue("failed" in result.message.lower())

    @patch("requests.patch")
    def test_update_catalog_item_variable(self, mock_patch):
        """Test update_catalog_item_variable function."""
        # Configure mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "var1",
                "question_text": "Updated Variable",
                "mandatory": "true",
                "help_text": "This is help text",
            }
        }
        mock_patch.return_value = mock_response

        # Create test params
        params = UpdateCatalogItemVariableParams(
            variable_id="var1",
            label="Updated Variable",
            mandatory=True,
            help_text="This is help text",
        )

        # Call function
        result = update_catalog_item_variable(self.config, self.auth_manager, params)

        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.variable_id, "var1")
        self.assertIsNotNone(result.details)

        # Verify mock was called correctly
        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        self.assertEqual(
            call_args[0][0],
            f"{self.config.instance_url}/api/now/table/item_option_new/var1",
        )
        self.assertEqual(call_args[1]["json"]["question_text"], "Updated Variable")
        self.assertEqual(call_args[1]["json"]["mandatory"], "true")
        self.assertEqual(call_args[1]["json"]["help_text"], "This is help text")

    @patch("requests.patch")
    def test_update_catalog_item_variable_no_params(self, mock_patch):
        """Test update_catalog_item_variable function with no update parameters."""
        # Create test params with no updates (only ID)
        params = UpdateCatalogItemVariableParams(
            variable_id="var1",
        )

        # Call function
        result = update_catalog_item_variable(self.config, self.auth_manager, params)

        # Verify result - should fail since no update parameters provided
        self.assertFalse(result.success)
        self.assertEqual(result.message, "No update parameters provided")

        # Verify mock was not called
        mock_patch.assert_not_called()

    @patch("requests.patch")
    def test_update_catalog_item_variable_error(self, mock_patch):
        """Test update_catalog_item_variable function with error."""
        # Configure mock to raise exception
        mock_patch.side_effect = requests.RequestException("Test error")

        # Create test params
        params = UpdateCatalogItemVariableParams(
            variable_id="var1",
            label="Updated Variable",
        )

        # Call function
        result = update_catalog_item_variable(self.config, self.auth_manager, params)

        # Verify result
        self.assertFalse(result.success)
        self.assertTrue("failed" in result.message.lower())


if __name__ == "__main__":
    unittest.main() 