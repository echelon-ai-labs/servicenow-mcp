"""
Service Catalog tools for the ServiceNow MCP server.

This module provides tools for querying and viewing the service catalog in ServiceNow.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ListCatalogItemsParams(BaseModel):
    """Parameters for listing service catalog items."""
    
    limit: int = Field(10, description="Maximum number of catalog items to return")
    offset: int = Field(0, description="Offset for pagination")
    category: Optional[str] = Field(None, description="Filter by category")
    query: Optional[str] = Field(None, description="Search query for catalog items")
    active: bool = Field(True, description="Whether to only return active catalog items")


class GetCatalogItemParams(BaseModel):
    """Parameters for getting a specific service catalog item."""
    
    item_id: str = Field(..., description="Catalog item ID or sys_id")


class ListCatalogCategoriesParams(BaseModel):
    """Parameters for listing service catalog categories."""
    
    limit: int = Field(10, description="Maximum number of categories to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for categories")
    active: bool = Field(True, description="Whether to only return active categories")


class CatalogResponse(BaseModel):
    """Response from catalog operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


class CreateCatalogCategoryParams(BaseModel):
    """Parameters for creating a new service catalog category."""
    
    title: str = Field(..., description="Title of the category")
    description: Optional[str] = Field(None, description="Description of the category")
    parent: Optional[str] = Field(None, description="Parent category sys_id")
    icon: Optional[str] = Field(None, description="Icon for the category")
    active: bool = Field(True, description="Whether the category is active")
    order: Optional[int] = Field(None, description="Order of the category")


class UpdateCatalogCategoryParams(BaseModel):
    """Parameters for updating a service catalog category."""
    
    category_id: str = Field(..., description="Category ID or sys_id")
    title: Optional[str] = Field(None, description="Title of the category")
    description: Optional[str] = Field(None, description="Description of the category")
    parent: Optional[str] = Field(None, description="Parent category sys_id")
    icon: Optional[str] = Field(None, description="Icon for the category")
    active: Optional[bool] = Field(None, description="Whether the category is active")
    order: Optional[int] = Field(None, description="Order of the category")


class MoveCatalogItemsParams(BaseModel):
    """Parameters for moving catalog items between categories."""
    
    item_ids: List[str] = Field(..., description="List of catalog item IDs to move")
    target_category_id: str = Field(..., description="Target category ID to move items to")


def list_catalog_items(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCatalogItemsParams,
) -> Dict[str, Any]:
    """
    List service catalog items from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing catalog items

    Returns:
        Dictionary containing catalog items and metadata
    """
    logger.info("Listing service catalog items")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/sc_cat_item"
    
    # Prepare query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Add filters
    filters = []
    if params.active:
        filters.append("active=true")
    if params.category:
        filters.append(f"category={params.category}")
    if params.query:
        filters.append(f"short_descriptionLIKE{params.query}^ORnameLIKE{params.query}")
    
    if filters:
        query_params["sysparm_query"] = "^".join(filters)
    
    # Make the API request
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    
    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        items = result.get("result", [])
        
        # Format the response
        formatted_items = []
        for item in items:
            formatted_items.append({
                "sys_id": item.get("sys_id", ""),
                "name": item.get("name", ""),
                "short_description": item.get("short_description", ""),
                "category": item.get("category", ""),
                "price": item.get("price", ""),
                "picture": item.get("picture", ""),
                "active": item.get("active", ""),
                "order": item.get("order", ""),
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(formatted_items)} catalog items",
            "items": formatted_items,
            "total": len(formatted_items),
            "limit": params.limit,
            "offset": params.offset,
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing catalog items: {str(e)}")
        return {
            "success": False,
            "message": f"Error listing catalog items: {str(e)}",
            "items": [],
            "total": 0,
            "limit": params.limit,
            "offset": params.offset,
        }


def get_catalog_item(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetCatalogItemParams,
) -> CatalogResponse:
    """
    Get a specific service catalog item from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting a catalog item

    Returns:
        Response containing the catalog item details
    """
    logger.info(f"Getting service catalog item: {params.item_id}")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/sc_cat_item/{params.item_id}"
    
    # Prepare query parameters
    query_params = {
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Make the API request
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    
    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        item = result.get("result", {})
        
        if not item:
            return CatalogResponse(
                success=False,
                message=f"Catalog item not found: {params.item_id}",
                data=None,
            )
        
        # Format the response
        formatted_item = {
            "sys_id": item.get("sys_id", ""),
            "name": item.get("name", ""),
            "short_description": item.get("short_description", ""),
            "description": item.get("description", ""),
            "category": item.get("category", ""),
            "price": item.get("price", ""),
            "picture": item.get("picture", ""),
            "active": item.get("active", ""),
            "order": item.get("order", ""),
            "delivery_time": item.get("delivery_time", ""),
            "availability": item.get("availability", ""),
            "variables": get_catalog_item_variables(config, auth_manager, params.item_id),
        }
        
        return CatalogResponse(
            success=True,
            message=f"Retrieved catalog item: {item.get('name', '')}",
            data=formatted_item,
        )
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting catalog item: {str(e)}")
        return CatalogResponse(
            success=False,
            message=f"Error getting catalog item: {str(e)}",
            data=None,
        )


def get_catalog_item_variables(
    config: ServerConfig,
    auth_manager: AuthManager,
    item_id: str,
) -> List[Dict[str, Any]]:
    """
    Get variables for a specific service catalog item.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        item_id: Catalog item ID or sys_id

    Returns:
        List of variables for the catalog item
    """
    logger.info(f"Getting variables for catalog item: {item_id}")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/item_option_new"
    
    # Prepare query parameters
    query_params = {
        "sysparm_query": f"cat_item={item_id}^ORDERBYorder",
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Make the API request
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    
    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        variables = result.get("result", [])
        
        # Format the response
        formatted_variables = []
        for variable in variables:
            formatted_variables.append({
                "sys_id": variable.get("sys_id", ""),
                "name": variable.get("name", ""),
                "label": variable.get("question_text", ""),
                "type": variable.get("type", ""),
                "mandatory": variable.get("mandatory", ""),
                "default_value": variable.get("default_value", ""),
                "help_text": variable.get("help_text", ""),
                "order": variable.get("order", ""),
            })
        
        return formatted_variables
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting catalog item variables: {str(e)}")
        return []


def list_catalog_categories(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListCatalogCategoriesParams,
) -> Dict[str, Any]:
    """
    List service catalog categories from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing catalog categories

    Returns:
        Dictionary containing catalog categories and metadata
    """
    logger.info("Listing service catalog categories")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/sc_category"
    
    # Prepare query parameters
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
    }
    
    # Add filters
    filters = []
    if params.active:
        filters.append("active=true")
    if params.query:
        filters.append(f"titleLIKE{params.query}^ORdescriptionLIKE{params.query}")
    
    if filters:
        query_params["sysparm_query"] = "^".join(filters)
    
    # Make the API request
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    
    try:
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        categories = result.get("result", [])
        
        # Format the response
        formatted_categories = []
        for category in categories:
            formatted_categories.append({
                "sys_id": category.get("sys_id", ""),
                "title": category.get("title", ""),
                "description": category.get("description", ""),
                "parent": category.get("parent", ""),
                "icon": category.get("icon", ""),
                "active": category.get("active", ""),
                "order": category.get("order", ""),
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(formatted_categories)} catalog categories",
            "categories": formatted_categories,
            "total": len(formatted_categories),
            "limit": params.limit,
            "offset": params.offset,
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing catalog categories: {str(e)}")
        return {
            "success": False,
            "message": f"Error listing catalog categories: {str(e)}",
            "categories": [],
            "total": 0,
            "limit": params.limit,
            "offset": params.offset,
        }


def create_catalog_category(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: CreateCatalogCategoryParams,
) -> CatalogResponse:
    """
    Create a new service catalog category in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating a catalog category

    Returns:
        Response containing the result of the operation
    """
    logger.info("Creating new service catalog category")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/sc_category"
    
    # Prepare request body
    body = {
        "title": params.title,
    }
    
    if params.description is not None:
        body["description"] = params.description
    if params.parent is not None:
        body["parent"] = params.parent
    if params.icon is not None:
        body["icon"] = params.icon
    if params.active is not None:
        body["active"] = str(params.active).lower()
    if params.order is not None:
        body["order"] = str(params.order)
    
    # Make the API request
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        category = result.get("result", {})
        
        # Format the response
        formatted_category = {
            "sys_id": category.get("sys_id", ""),
            "title": category.get("title", ""),
            "description": category.get("description", ""),
            "parent": category.get("parent", ""),
            "icon": category.get("icon", ""),
            "active": category.get("active", ""),
            "order": category.get("order", ""),
        }
        
        return CatalogResponse(
            success=True,
            message=f"Created catalog category: {params.title}",
            data=formatted_category,
        )
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating catalog category: {str(e)}")
        return CatalogResponse(
            success=False,
            message=f"Error creating catalog category: {str(e)}",
            data=None,
        )


def update_catalog_category(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: UpdateCatalogCategoryParams,
) -> CatalogResponse:
    """
    Update an existing service catalog category in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating a catalog category

    Returns:
        Response containing the result of the operation
    """
    logger.info(f"Updating service catalog category: {params.category_id}")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/sc_category/{params.category_id}"
    
    # Prepare request body with only the provided parameters
    body = {}
    if params.title is not None:
        body["title"] = params.title
    if params.description is not None:
        body["description"] = params.description
    if params.parent is not None:
        body["parent"] = params.parent
    if params.icon is not None:
        body["icon"] = params.icon
    if params.active is not None:
        body["active"] = str(params.active).lower()
    if params.order is not None:
        body["order"] = str(params.order)
    
    # Make the API request
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    
    try:
        response = requests.patch(url, headers=headers, json=body)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        category = result.get("result", {})
        
        # Format the response
        formatted_category = {
            "sys_id": category.get("sys_id", ""),
            "title": category.get("title", ""),
            "description": category.get("description", ""),
            "parent": category.get("parent", ""),
            "icon": category.get("icon", ""),
            "active": category.get("active", ""),
            "order": category.get("order", ""),
        }
        
        return CatalogResponse(
            success=True,
            message=f"Updated catalog category: {params.category_id}",
            data=formatted_category,
        )
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating catalog category: {str(e)}")
        return CatalogResponse(
            success=False,
            message=f"Error updating catalog category: {str(e)}",
            data=None,
        )


def move_catalog_items(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MoveCatalogItemsParams,
) -> CatalogResponse:
    """
    Move catalog items to a different category.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for moving catalog items

    Returns:
        Response containing the result of the operation
    """
    logger.info(f"Moving {len(params.item_ids)} catalog items to category: {params.target_category_id}")
    
    # Build the API URL
    url = f"{config.instance_url}/api/now/table/sc_cat_item"
    
    # Make the API request for each item
    headers = auth_manager.get_headers()
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    
    success_count = 0
    failed_items = []
    
    try:
        for item_id in params.item_ids:
            item_url = f"{url}/{item_id}"
            body = {
                "category": params.target_category_id
            }
            
            try:
                response = requests.patch(item_url, headers=headers, json=body)
                response.raise_for_status()
                success_count += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Error moving catalog item {item_id}: {str(e)}")
                failed_items.append({"item_id": item_id, "error": str(e)})
        
        # Prepare the response
        if success_count == len(params.item_ids):
            return CatalogResponse(
                success=True,
                message=f"Successfully moved {success_count} catalog items to category {params.target_category_id}",
                data={"moved_items_count": success_count},
            )
        elif success_count > 0:
            return CatalogResponse(
                success=True,
                message=f"Partially moved catalog items. {success_count} succeeded, {len(failed_items)} failed.",
                data={
                    "moved_items_count": success_count,
                    "failed_items": failed_items,
                },
            )
        else:
            return CatalogResponse(
                success=False,
                message="Failed to move any catalog items",
                data={"failed_items": failed_items},
            )
    
    except Exception as e:
        logger.error(f"Error moving catalog items: {str(e)}")
        return CatalogResponse(
            success=False,
            message=f"Error moving catalog items: {str(e)}",
            data=None,
        ) 