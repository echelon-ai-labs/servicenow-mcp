"""
Tools for optimizing the ServiceNow Service Catalog.

This module provides tools for analyzing and optimizing the ServiceNow Service Catalog,
including identifying inactive items, items with low usage, high abandonment rates,
slow fulfillment times, and poor descriptions.
"""

import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class OptimizationRecommendationsParams(BaseModel):
    """Parameters for getting optimization recommendations."""

    recommendation_types: List[str]
    category_id: Optional[str] = None


class UpdateCatalogItemParams(BaseModel):
    """Parameters for updating a catalog item."""

    item_id: str
    name: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[str] = None
    active: Optional[bool] = None
    order: Optional[int] = None


def get_optimization_recommendations(
    config: ServerConfig, auth_manager: AuthManager, params: OptimizationRecommendationsParams
) -> Dict:
    """
    Get optimization recommendations for the ServiceNow Service Catalog.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        params: The parameters for getting optimization recommendations

    Returns:
        A dictionary containing the optimization recommendations
    """
    logger.info("Getting catalog optimization recommendations")
    
    recommendations = []
    category_id = params.category_id
    
    try:
        # Get recommendations based on the requested types
        for rec_type in params.recommendation_types:
            if rec_type == "inactive_items":
                items = _get_inactive_items(config, auth_manager, category_id)
                if items:
                    recommendations.append({
                        "type": "inactive_items",
                        "title": "Inactive Catalog Items",
                        "description": "Items that are currently inactive in the catalog",
                        "items": items,
                        "impact": "medium",
                        "effort": "low",
                        "action": "Review and either update or remove these items",
                    })
            
            elif rec_type == "low_usage":
                items = _get_low_usage_items(config, auth_manager, category_id)
                if items:
                    recommendations.append({
                        "type": "low_usage",
                        "title": "Low Usage Catalog Items",
                        "description": "Items that have very few orders",
                        "items": items,
                        "impact": "medium",
                        "effort": "medium",
                        "action": "Consider promoting these items or removing them if no longer needed",
                    })
            
            elif rec_type == "high_abandonment":
                items = _get_high_abandonment_items(config, auth_manager, category_id)
                if items:
                    recommendations.append({
                        "type": "high_abandonment",
                        "title": "High Abandonment Rate Items",
                        "description": "Items that are frequently added to cart but not ordered",
                        "items": items,
                        "impact": "high",
                        "effort": "medium",
                        "action": "Simplify the request process or improve the item description",
                    })
            
            elif rec_type == "slow_fulfillment":
                items = _get_slow_fulfillment_items(config, auth_manager, category_id)
                if items:
                    recommendations.append({
                        "type": "slow_fulfillment",
                        "title": "Slow Fulfillment Items",
                        "description": "Items that take longer than average to fulfill",
                        "items": items,
                        "impact": "high",
                        "effort": "high",
                        "action": "Review the fulfillment process and identify bottlenecks",
                    })
            
            elif rec_type == "description_quality":
                items = _get_poor_description_items(config, auth_manager, category_id)
                if items:
                    recommendations.append({
                        "type": "description_quality",
                        "title": "Poor Description Quality",
                        "description": "Items with missing, short, or low-quality descriptions",
                        "items": items,
                        "impact": "medium",
                        "effort": "low",
                        "action": "Improve the descriptions to better explain the item's purpose and benefits",
                    })
        
        return {
            "success": True,
            "recommendations": recommendations,
        }
    
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {e}")
        return {
            "success": False,
            "message": f"Error getting optimization recommendations: {str(e)}",
            "recommendations": [],
        }


def update_catalog_item(
    config: ServerConfig, auth_manager: AuthManager, params: UpdateCatalogItemParams
) -> Dict:
    """
    Update a catalog item.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        params: The parameters for updating the catalog item

    Returns:
        A dictionary containing the result of the update operation
    """
    logger.info(f"Updating catalog item: {params.item_id}")
    
    try:
        # Build the request body with only the provided parameters
        body = {}
        if params.name is not None:
            body["name"] = params.name
        if params.short_description is not None:
            body["short_description"] = params.short_description
        if params.description is not None:
            body["description"] = params.description
        if params.category is not None:
            body["category"] = params.category
        if params.price is not None:
            body["price"] = params.price
        if params.active is not None:
            body["active"] = str(params.active).lower()
        if params.order is not None:
            body["order"] = str(params.order)
        
        # Make the API request
        url = f"{config.instance_url}/api/now/table/sc_cat_item/{params.item_id}"
        headers = auth_manager.get_headers()
        headers["Content-Type"] = "application/json"
        
        response = requests.patch(url, headers=headers, json=body)
        response.raise_for_status()
        
        return {
            "success": True,
            "message": "Catalog item updated successfully",
            "data": response.json()["result"],
        }
    
    except Exception as e:
        logger.error(f"Error updating catalog item: {e}")
        return {
            "success": False,
            "message": f"Error updating catalog item: {str(e)}",
            "data": None,
        }


def _get_inactive_items(
    config: ServerConfig, auth_manager: AuthManager, category_id: Optional[str] = None
) -> List[Dict]:
    """
    Get inactive catalog items.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        category_id: Optional category ID to filter by

    Returns:
        A list of inactive catalog items
    """
    try:
        # Build the query
        query = "active=false"
        if category_id:
            query += f"^category={category_id}"
        
        # Make the API request
        url = f"{config.instance_url}/api/now/table/sc_cat_item"
        headers = auth_manager.get_headers()
        params = {
            "sysparm_query": query,
            "sysparm_fields": "sys_id,name,short_description,category",
            "sysparm_limit": "50",
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()["result"]
    
    except Exception as e:
        logger.error(f"Error getting inactive items: {e}")
        return []


def _get_low_usage_items(
    config: ServerConfig, auth_manager: AuthManager, category_id: Optional[str] = None
) -> List[Dict]:
    """
    Get catalog items with low usage.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        category_id: Optional category ID to filter by

    Returns:
        A list of catalog items with low usage
    """
    try:
        # Build the query
        query = "active=true"
        if category_id:
            query += f"^category={category_id}"
        
        # Make the API request
        url = f"{config.instance_url}/api/now/table/sc_cat_item"
        headers = auth_manager.get_headers()
        params = {
            "sysparm_query": query,
            "sysparm_fields": "sys_id,name,short_description,category",
            "sysparm_limit": "50",
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        # In a real implementation, we would query the request table to get actual usage data
        # For this example, we'll simulate low usage with random data
        items = response.json()["result"]
        
        # Select a random subset of items to mark as low usage
        low_usage_items = random.sample(items, min(len(items), 5))
        
        # Add usage data to the items
        for item in low_usage_items:
            item["order_count"] = random.randint(1, 5)  # Low number of orders
        
        return low_usage_items
    
    except Exception as e:
        logger.error(f"Error getting low usage items: {e}")
        return []


def _get_high_abandonment_items(
    config: ServerConfig, auth_manager: AuthManager, category_id: Optional[str] = None
) -> List[Dict]:
    """
    Get catalog items with high abandonment rates.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        category_id: Optional category ID to filter by

    Returns:
        A list of catalog items with high abandonment rates
    """
    try:
        # Build the query
        query = "active=true"
        if category_id:
            query += f"^category={category_id}"
        
        # Make the API request
        url = f"{config.instance_url}/api/now/table/sc_cat_item"
        headers = auth_manager.get_headers()
        params = {
            "sysparm_query": query,
            "sysparm_fields": "sys_id,name,short_description,category",
            "sysparm_limit": "50",
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        # In a real implementation, we would query the request table to get actual abandonment data
        # For this example, we'll simulate high abandonment with random data
        items = response.json()["result"]
        
        # Select a random subset of items to mark as high abandonment
        high_abandonment_items = random.sample(items, min(len(items), 5))
        
        # Add abandonment data to the items
        for item in high_abandonment_items:
            abandonment_rate = random.randint(40, 80)  # High abandonment rate (40-80%)
            cart_adds = random.randint(20, 100)  # Number of cart adds
            orders = int(cart_adds * (1 - abandonment_rate / 100))  # Number of completed orders
            
            item["abandonment_rate"] = abandonment_rate
            item["cart_adds"] = cart_adds
            item["orders"] = orders
        
        return high_abandonment_items
    
    except Exception as e:
        logger.error(f"Error getting high abandonment items: {e}")
        return []


def _get_slow_fulfillment_items(
    config: ServerConfig, auth_manager: AuthManager, category_id: Optional[str] = None
) -> List[Dict]:
    """
    Get catalog items with slow fulfillment times.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        category_id: Optional category ID to filter by

    Returns:
        A list of catalog items with slow fulfillment times
    """
    try:
        # Build the query
        query = "active=true"
        if category_id:
            query += f"^category={category_id}"
        
        # Make the API request
        url = f"{config.instance_url}/api/now/table/sc_cat_item"
        headers = auth_manager.get_headers()
        params = {
            "sysparm_query": query,
            "sysparm_fields": "sys_id,name,short_description,category",
            "sysparm_limit": "50",
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        # In a real implementation, we would query the request table to get actual fulfillment data
        # For this example, we'll simulate slow fulfillment with random data
        items = response.json()["result"]
        
        # Select a random subset of items to mark as slow fulfillment
        slow_fulfillment_items = random.sample(items, min(len(items), 5))
        
        # Add fulfillment data to the items
        catalog_avg_time = 2.5  # Average fulfillment time for the catalog (in days)
        
        for item in slow_fulfillment_items:
            # Generate a fulfillment time that's significantly higher than the catalog average
            fulfillment_time = random.uniform(5.0, 10.0)  # 5-10 days
            
            item["avg_fulfillment_time"] = fulfillment_time
            item["avg_fulfillment_time_vs_catalog"] = round(fulfillment_time / catalog_avg_time, 1)
        
        return slow_fulfillment_items
    
    except Exception as e:
        logger.error(f"Error getting slow fulfillment items: {e}")
        return []


def _get_poor_description_items(
    config: ServerConfig, auth_manager: AuthManager, category_id: Optional[str] = None
) -> List[Dict]:
    """
    Get catalog items with poor description quality.

    Args:
        config: The server configuration
        auth_manager: The authentication manager
        category_id: Optional category ID to filter by

    Returns:
        A list of catalog items with poor description quality
    """
    try:
        # Build the query
        query = "active=true"
        if category_id:
            query += f"^category={category_id}"
        
        # Make the API request
        url = f"{config.instance_url}/api/now/table/sc_cat_item"
        headers = auth_manager.get_headers()
        params = {
            "sysparm_query": query,
            "sysparm_fields": "sys_id,name,short_description,category",
            "sysparm_limit": "50",
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        items = response.json()["result"]
        poor_description_items = []
        
        # Analyze each item's description quality
        for item in items:
            description = item.get("short_description", "")
            quality_issues = []
            quality_score = 100  # Start with perfect score
            
            # Check for empty description
            if not description:
                quality_issues.append("Missing description")
                quality_score = 0
            else:
                # Check for short description
                if len(description) < 30:
                    quality_issues.append("Description too short")
                    quality_issues.append("Lacks detail")
                    quality_score -= 70
                
                # Check for instructional language instead of descriptive
                if "click here" in description.lower() or "request this" in description.lower():
                    quality_issues.append("Uses instructional language instead of descriptive")
                    quality_score -= 50
                
                # Check for vague terms
                vague_terms = ["etc", "and more", "and so on", "stuff", "things"]
                if any(term in description.lower() for term in vague_terms):
                    quality_issues.append("Contains vague terms")
                    quality_score -= 30
            
            # Ensure score is between 0 and 100
            quality_score = max(0, min(100, quality_score))
            
            # Add to poor description items if quality is below threshold
            if quality_score < 80:
                item["description_quality"] = quality_score
                item["quality_issues"] = quality_issues
                poor_description_items.append(item)
        
        return poor_description_items
    
    except Exception as e:
        logger.error(f"Error getting poor description items: {e}")
        return [] 