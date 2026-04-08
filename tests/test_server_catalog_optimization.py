"""
Tests for the ServiceNow MCP server integration with catalog optimization tools.
"""

import unittest

from servicenow_mcp.tools.catalog_optimization import (
    OptimizationRecommendationsParams,
    UpdateCatalogItemParams,
)


class TestCatalogOptimizationToolParameters(unittest.TestCase):
    """Test cases for the catalog optimization tool parameters."""

    def test_tool_parameter_classes(self):
        """Test that the parameter classes for the tools are properly defined."""
        # Test OptimizationRecommendationsParams
        params = OptimizationRecommendationsParams(
            recommendation_types=["inactive_items", "low_usage"],
            category_id="hardware"
        )
        self.assertEqual(params.recommendation_types, ["inactive_items", "low_usage"])
        self.assertEqual(params.category_id, "hardware")

        # Test with default values
        params = OptimizationRecommendationsParams(
            recommendation_types=["inactive_items"]
        )
        self.assertEqual(params.recommendation_types, ["inactive_items"])
        self.assertIsNone(params.category_id)

        # Test UpdateCatalogItemParams
        params = UpdateCatalogItemParams(
            item_id="item1",
            name="Updated Laptop",
            short_description="High-performance laptop",
            description="Detailed description of the laptop",
            category="hardware",
            price="1099.99",
            active=True,
            order=100
        )
        self.assertEqual(params.item_id, "item1")
        self.assertEqual(params.name, "Updated Laptop")
        self.assertEqual(params.short_description, "High-performance laptop")
        self.assertEqual(params.description, "Detailed description of the laptop")
        self.assertEqual(params.category, "hardware")
        self.assertEqual(params.price, "1099.99")
        self.assertTrue(params.active)
        self.assertEqual(params.order, 100)

        # Test with only required parameters
        params = UpdateCatalogItemParams(
            item_id="item1"
        )
        self.assertEqual(params.item_id, "item1")
        self.assertIsNone(params.name)
        self.assertIsNone(params.short_description)
        self.assertIsNone(params.description)
        self.assertIsNone(params.category)
        self.assertIsNone(params.price)
        self.assertIsNone(params.active)
        self.assertIsNone(params.order)


if __name__ == "__main__":
    unittest.main() 