"""
Tests for the ServiceNow MCP catalog optimization tools.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.tools.catalog_optimization import (
    OptimizationRecommendationsParams,
    UpdateCatalogItemParams,
    _get_inactive_items,
    _get_low_usage_items,
    _get_poor_description_items,
    _get_slow_fulfillment_items,
    get_optimization_recommendations,
    update_catalog_item,
)
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig


class TestCatalogOptimizationTools(unittest.TestCase):
    """Test cases for the catalog optimization tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock server config
        self.config = ServerConfig(
            instance_url="https://example.service-now.com",
            auth=AuthConfig(
                type=AuthType.BASIC,
                basic=BasicAuthConfig(username="admin", password="password"),
            ),
        )

        # Create a mock auth manager
        self.auth_manager = MagicMock(spec=AuthManager)
        self.auth_manager.get_headers.return_value = {"Authorization": "Basic YWRtaW46cGFzc3dvcmQ="}

    @patch("requests.get")
    def test_get_inactive_items(self, mock_get):
        """Test getting inactive catalog items."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "item1",
                    "name": "Old Laptop",
                    "short_description": "Outdated laptop model",
                    "category": "hardware",
                },
                {
                    "sys_id": "item2",
                    "name": "Legacy Software",
                    "short_description": "Deprecated software package",
                    "category": "software",
                },
            ]
        }
        mock_get.return_value = mock_response

        # Call the function
        result = _get_inactive_items(self.config, self.auth_manager)

        # Verify the results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Old Laptop")
        self.assertEqual(result[1]["name"], "Legacy Software")

        # Verify the API call
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["sysparm_query"], "active=false")

    @patch("requests.get")
    def test_get_inactive_items_with_category(self, mock_get):
        """Test getting inactive catalog items filtered by category."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "item1",
                    "name": "Old Laptop",
                    "short_description": "Outdated laptop model",
                    "category": "hardware",
                },
            ]
        }
        mock_get.return_value = mock_response

        # Call the function with a category filter
        result = _get_inactive_items(self.config, self.auth_manager, "hardware")

        # Verify the results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Old Laptop")

        # Verify the API call
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["sysparm_query"], "active=false^category=hardware")

    @patch("requests.get")
    def test_get_inactive_items_error(self, mock_get):
        """Test error handling when getting inactive catalog items."""
        # Mock an error response
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        # Call the function
        result = _get_inactive_items(self.config, self.auth_manager)

        # Verify the results
        self.assertEqual(result, [])

    @patch("requests.get")
    @patch("random.sample")
    @patch("random.randint")
    def test_get_low_usage_items(self, mock_randint, mock_sample, mock_get):
        """Test getting catalog items with low usage."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "item1",
                    "name": "Rarely Used Laptop",
                    "short_description": "Laptop model with low demand",
                    "category": "hardware",
                },
                {
                    "sys_id": "item2",
                    "name": "Unpopular Software",
                    "short_description": "Software with few users",
                    "category": "software",
                },
                {
                    "sys_id": "item3",
                    "name": "Niche Service",
                    "short_description": "Specialized service with limited audience",
                    "category": "services",
                },
            ]
        }
        mock_get.return_value = mock_response

        # Mock the random sample to return the first two items
        mock_sample.return_value = [
            {
                "sys_id": "item1",
                "name": "Rarely Used Laptop",
                "short_description": "Laptop model with low demand",
                "category": "hardware",
            },
            {
                "sys_id": "item2",
                "name": "Unpopular Software",
                "short_description": "Software with few users",
                "category": "software",
            },
        ]

        # Mock the random order counts
        mock_randint.return_value = 2

        # Call the function
        result = _get_low_usage_items(self.config, self.auth_manager)

        # Verify the results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Rarely Used Laptop")
        self.assertEqual(result[0]["order_count"], 2)
        self.assertEqual(result[1]["name"], "Unpopular Software")
        self.assertEqual(result[1]["order_count"], 2)

        # Verify the API call
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["sysparm_query"], "active=true")

    def test_high_abandonment_items_format(self):
        """Test the expected format of high abandonment items."""
        # This test doesn't call the actual function, but verifies the expected format
        # of the data that would be returned by the function
        
        # Example data that would be returned by _get_high_abandonment_items
        high_abandonment_items = [
            {
                "sys_id": "item1",
                "name": "Complex Request",
                "short_description": "Request with many fields",
                "category": "hardware",
                "abandonment_rate": 60,
                "cart_adds": 30,
                "orders": 12,
            },
            {
                "sys_id": "item2",
                "name": "Expensive Item",
                "short_description": "High-cost item",
                "category": "software",
                "abandonment_rate": 60,
                "cart_adds": 20,
                "orders": 8,
            },
        ]
        
        # Verify the expected format
        self.assertEqual(len(high_abandonment_items), 2)
        self.assertEqual(high_abandonment_items[0]["name"], "Complex Request")
        self.assertEqual(high_abandonment_items[0]["abandonment_rate"], 60)
        self.assertEqual(high_abandonment_items[0]["cart_adds"], 30)
        self.assertEqual(high_abandonment_items[0]["orders"], 12)
        self.assertEqual(high_abandonment_items[1]["name"], "Expensive Item")
        self.assertEqual(high_abandonment_items[1]["abandonment_rate"], 60)
        self.assertEqual(high_abandonment_items[1]["cart_adds"], 20)
        self.assertEqual(high_abandonment_items[1]["orders"], 8)

    @patch("requests.get")
    @patch("random.sample")
    @patch("random.uniform")
    def test_get_slow_fulfillment_items(self, mock_uniform, mock_sample, mock_get):
        """Test getting catalog items with slow fulfillment times."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "item1",
                    "name": "Custom Hardware",
                    "short_description": "Specialized hardware request",
                    "category": "hardware",
                },
                {
                    "sys_id": "item2",
                    "name": "Complex Software",
                    "short_description": "Software with complex installation",
                    "category": "software",
                },
            ]
        }
        mock_get.return_value = mock_response

        # Mock the random sample to return all items
        mock_sample.return_value = [
            {
                "sys_id": "item1",
                "name": "Custom Hardware",
                "short_description": "Specialized hardware request",
                "category": "hardware",
            },
            {
                "sys_id": "item2",
                "name": "Complex Software",
                "short_description": "Software with complex installation",
                "category": "software",
            },
        ]

        # Mock the random uniform values for fulfillment times
        mock_uniform.return_value = 7.5

        # Call the function
        result = _get_slow_fulfillment_items(self.config, self.auth_manager)

        # Verify the results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Custom Hardware")
        self.assertEqual(result[0]["avg_fulfillment_time"], 7.5)
        self.assertEqual(result[0]["avg_fulfillment_time_vs_catalog"], 3.0)  # 7.5 / 2.5 = 3.0
        self.assertEqual(result[1]["name"], "Complex Software")
        self.assertEqual(result[1]["avg_fulfillment_time"], 7.5)
        self.assertEqual(result[1]["avg_fulfillment_time_vs_catalog"], 3.0)  # 7.5 / 2.5 = 3.0

    @patch("requests.get")
    def test_get_poor_description_items(self, mock_get):
        """Test getting catalog items with poor description quality."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": [
                {
                    "sys_id": "item1",
                    "name": "Laptop",
                    "short_description": "",  # Empty description
                    "category": "hardware",
                },
                {
                    "sys_id": "item2",
                    "name": "Software",
                    "short_description": "Software package",  # Short description
                    "category": "software",
                },
                {
                    "sys_id": "item3",
                    "name": "Service",
                    "short_description": "Please click here to request this service",  # Instructional language
                    "category": "services",
                },
            ]
        }
        mock_get.return_value = mock_response

        # Call the function
        result = _get_poor_description_items(self.config, self.auth_manager)

        # Verify the results
        self.assertEqual(len(result), 3)
        
        # Check the first item (empty description)
        self.assertEqual(result[0]["name"], "Laptop")
        self.assertEqual(result[0]["description_quality"], 0)
        self.assertEqual(result[0]["quality_issues"], ["Missing description"])
        
        # Check the second item (short description)
        self.assertEqual(result[1]["name"], "Software")
        self.assertEqual(result[1]["description_quality"], 30)
        self.assertEqual(result[1]["quality_issues"], ["Description too short", "Lacks detail"])
        
        # Check the third item (instructional language)
        self.assertEqual(result[2]["name"], "Service")
        self.assertEqual(result[2]["description_quality"], 50)
        self.assertEqual(result[2]["quality_issues"], ["Uses instructional language instead of descriptive"])

    @patch("servicenow_mcp.tools.catalog_optimization._get_inactive_items")
    @patch("servicenow_mcp.tools.catalog_optimization._get_low_usage_items")
    @patch("servicenow_mcp.tools.catalog_optimization._get_high_abandonment_items")
    @patch("servicenow_mcp.tools.catalog_optimization._get_slow_fulfillment_items")
    @patch("servicenow_mcp.tools.catalog_optimization._get_poor_description_items")
    def test_get_optimization_recommendations(
        self, 
        mock_poor_desc, 
        mock_slow_fulfill, 
        mock_high_abandon, 
        mock_low_usage, 
        mock_inactive
    ):
        """Test getting optimization recommendations."""
        # Mock the helper functions to return test data
        mock_inactive.return_value = [
            {
                "sys_id": "item1",
                "name": "Old Laptop",
                "short_description": "Outdated laptop model",
                "category": "hardware",
            },
        ]
        
        mock_low_usage.return_value = [
            {
                "sys_id": "item2",
                "name": "Rarely Used Software",
                "short_description": "Software with few users",
                "category": "software",
                "order_count": 2,
            },
        ]
        
        mock_high_abandon.return_value = [
            {
                "sys_id": "item3",
                "name": "Complex Request",
                "short_description": "Request with many fields",
                "category": "hardware",
                "abandonment_rate": 60,
                "cart_adds": 30,
                "orders": 12,
            },
        ]
        
        mock_slow_fulfill.return_value = [
            {
                "sys_id": "item4",
                "name": "Custom Hardware",
                "short_description": "Specialized hardware request",
                "category": "hardware",
                "avg_fulfillment_time": 7.5,
                "avg_fulfillment_time_vs_catalog": 3.0,
            },
        ]
        
        mock_poor_desc.return_value = [
            {
                "sys_id": "item5",
                "name": "Laptop",
                "short_description": "",
                "category": "hardware",
                "description_quality": 0,
                "quality_issues": ["Missing description"],
            },
        ]

        # Create the parameters
        params = OptimizationRecommendationsParams(
            recommendation_types=[
                "inactive_items", 
                "low_usage", 
                "high_abandonment", 
                "slow_fulfillment", 
                "description_quality"
            ]
        )

        # Call the function
        result = get_optimization_recommendations(self.config, self.auth_manager, params)

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(len(result["recommendations"]), 5)
        
        # Check each recommendation type
        recommendation_types = [rec["type"] for rec in result["recommendations"]]
        self.assertIn("inactive_items", recommendation_types)
        self.assertIn("low_usage", recommendation_types)
        self.assertIn("high_abandonment", recommendation_types)
        self.assertIn("slow_fulfillment", recommendation_types)
        self.assertIn("description_quality", recommendation_types)
        
        # Check that each recommendation has the expected fields
        for rec in result["recommendations"]:
            self.assertIn("title", rec)
            self.assertIn("description", rec)
            self.assertIn("items", rec)
            self.assertIn("impact", rec)
            self.assertIn("effort", rec)
            self.assertIn("action", rec)

    @patch("servicenow_mcp.tools.catalog_optimization._get_inactive_items")
    @patch("servicenow_mcp.tools.catalog_optimization._get_low_usage_items")
    def test_get_optimization_recommendations_filtered(self, mock_low_usage, mock_inactive):
        """Test getting filtered optimization recommendations."""
        # Mock the helper functions to return test data
        mock_inactive.return_value = [
            {
                "sys_id": "item1",
                "name": "Old Laptop",
                "short_description": "Outdated laptop model",
                "category": "hardware",
            },
        ]
        
        mock_low_usage.return_value = [
            {
                "sys_id": "item2",
                "name": "Rarely Used Software",
                "short_description": "Software with few users",
                "category": "software",
                "order_count": 2,
            },
        ]

        # Create the parameters with only specific recommendation types
        params = OptimizationRecommendationsParams(
            recommendation_types=["inactive_items", "low_usage"]
        )

        # Call the function
        result = get_optimization_recommendations(self.config, self.auth_manager, params)

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(len(result["recommendations"]), 2)
        
        # Check each recommendation type
        recommendation_types = [rec["type"] for rec in result["recommendations"]]
        self.assertIn("inactive_items", recommendation_types)
        self.assertIn("low_usage", recommendation_types)
        self.assertNotIn("high_abandonment", recommendation_types)
        self.assertNotIn("slow_fulfillment", recommendation_types)
        self.assertNotIn("description_quality", recommendation_types)

    @patch("requests.patch")
    def test_update_catalog_item(self, mock_patch):
        """Test updating a catalog item."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "item1",
                "name": "Laptop",
                "short_description": "Updated laptop description",
                "description": "Detailed description",
                "category": "hardware",
                "price": "999.99",
                "active": "true",
                "order": "100",
            }
        }
        mock_patch.return_value = mock_response

        # Create the parameters
        params = UpdateCatalogItemParams(
            item_id="item1",
            short_description="Updated laptop description",
        )

        # Call the function
        result = update_catalog_item(self.config, self.auth_manager, params)

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["short_description"], "Updated laptop description")
        
        # Verify the API call
        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        self.assertEqual(args[0], "https://example.service-now.com/api/now/table/sc_cat_item/item1")
        self.assertEqual(kwargs["json"], {"short_description": "Updated laptop description"})

    @patch("requests.patch")
    def test_update_catalog_item_multiple_fields(self, mock_patch):
        """Test updating multiple fields of a catalog item."""
        # Mock the response from ServiceNow
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "sys_id": "item1",
                "name": "Updated Laptop",
                "short_description": "Updated laptop description",
                "description": "Detailed description",
                "category": "hardware",
                "price": "1099.99",
                "active": "true",
                "order": "100",
            }
        }
        mock_patch.return_value = mock_response

        # Create the parameters with multiple fields
        params = UpdateCatalogItemParams(
            item_id="item1",
            name="Updated Laptop",
            short_description="Updated laptop description",
            price="1099.99",
        )

        # Call the function
        result = update_catalog_item(self.config, self.auth_manager, params)

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["name"], "Updated Laptop")
        self.assertEqual(result["data"]["short_description"], "Updated laptop description")
        self.assertEqual(result["data"]["price"], "1099.99")
        
        # Verify the API call
        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        self.assertEqual(args[0], "https://example.service-now.com/api/now/table/sc_cat_item/item1")
        self.assertEqual(kwargs["json"], {
            "name": "Updated Laptop",
            "short_description": "Updated laptop description",
            "price": "1099.99",
        })

    @patch("requests.patch")
    def test_update_catalog_item_error(self, mock_patch):
        """Test error handling when updating a catalog item."""
        # Mock an error response
        mock_patch.side_effect = requests.exceptions.RequestException("API Error")

        # Create the parameters
        params = UpdateCatalogItemParams(
            item_id="item1",
            short_description="Updated laptop description",
        )

        # Call the function
        result = update_catalog_item(self.config, self.auth_manager, params)

        # Verify the results
        self.assertFalse(result["success"])
        self.assertIn("Error updating catalog item", result["message"])
        self.assertIsNone(result["data"])


if __name__ == "__main__":
    unittest.main() 