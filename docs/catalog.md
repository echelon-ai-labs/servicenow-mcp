# ServiceNow Service Catalog Integration

This document provides information about the ServiceNow Service Catalog integration in the ServiceNow MCP server.

## Overview

The ServiceNow Service Catalog integration allows you to:

- List service catalog categories
- List service catalog items
- Get detailed information about specific catalog items, including their variables
- Filter catalog items by category or search query

## Tools

The following tools are available for interacting with the ServiceNow Service Catalog:

### `list_catalog_categories`

Lists available service catalog categories.

**Parameters:**
- `limit` (int, default: 10): Maximum number of categories to return
- `offset` (int, default: 0): Offset for pagination
- `query` (string, optional): Search query for categories
- `active` (boolean, default: true): Whether to only return active categories

**Example:**
```python
from servicenow_mcp.tools.catalog_tools import ListCatalogCategoriesParams, list_catalog_categories

params = ListCatalogCategoriesParams(
    limit=5,
    query="hardware"
)
result = list_catalog_categories(config, auth_manager, params)
```

### `create_catalog_category`

Creates a new service catalog category.

**Parameters:**
- `title` (string, required): Title of the category
- `description` (string, optional): Description of the category
- `parent` (string, optional): Parent category sys_id
- `icon` (string, optional): Icon for the category
- `active` (boolean, default: true): Whether the category is active
- `order` (integer, optional): Order of the category

**Example:**
```python
from servicenow_mcp.tools.catalog_tools import CreateCatalogCategoryParams, create_catalog_category

params = CreateCatalogCategoryParams(
    title="Cloud Services",
    description="Cloud-based services and resources",
    parent="parent_category_id",
    icon="cloud"
)
result = create_catalog_category(config, auth_manager, params)
```

### `update_catalog_category`

Updates an existing service catalog category.

**Parameters:**
- `category_id` (string, required): Category ID or sys_id
- `title` (string, optional): Title of the category
- `description` (string, optional): Description of the category
- `parent` (string, optional): Parent category sys_id
- `icon` (string, optional): Icon for the category
- `active` (boolean, optional): Whether the category is active
- `order` (integer, optional): Order of the category

**Example:**
```python
from servicenow_mcp.tools.catalog_tools import UpdateCatalogCategoryParams, update_catalog_category

params = UpdateCatalogCategoryParams(
    category_id="category123",
    title="IT Equipment",
    description="Updated description for IT equipment"
)
result = update_catalog_category(config, auth_manager, params)
```

### `move_catalog_items`

Moves catalog items to a different category.

**Parameters:**
- `item_ids` (list of strings, required): List of catalog item IDs to move
- `target_category_id` (string, required): Target category ID to move items to

**Example:**
```python
from servicenow_mcp.tools.catalog_tools import MoveCatalogItemsParams, move_catalog_items

params = MoveCatalogItemsParams(
    item_ids=["item1", "item2", "item3"],
    target_category_id="target_category_id"
)
result = move_catalog_items(config, auth_manager, params)
```

### `list_catalog_items`

Lists available service catalog items.

**Parameters:**
- `limit` (int, default: 10): Maximum number of items to return
- `offset` (int, default: 0): Offset for pagination
- `category` (string, optional): Filter by category
- `query` (string, optional): Search query for items
- `active` (boolean, default: true): Whether to only return active items

**Example:**
```python
from servicenow_mcp.tools.catalog_tools import ListCatalogItemsParams, list_catalog_items

params = ListCatalogItemsParams(
    limit=5,
    category="hardware",
    query="laptop"
)
result = list_catalog_items(config, auth_manager, params)
```

### `get_catalog_item`

Gets detailed information about a specific catalog item.

**Parameters:**
- `item_id` (string, required): Catalog item ID or sys_id

**Example:**
```python
from servicenow_mcp.tools.catalog_tools import GetCatalogItemParams, get_catalog_item

params = GetCatalogItemParams(
    item_id="item123"
)
result = get_catalog_item(config, auth_manager, params)
```

## Resources

The following resources are available for accessing the ServiceNow Service Catalog:

### `catalog://items`

Lists service catalog items.

**Example:**
```
catalog://items
```

### `catalog://categories`

Lists service catalog categories.

**Example:**
```
catalog://categories
```

### `catalog://{item_id}`

Gets a specific catalog item by ID.

**Example:**
```
catalog://item123
```

## Integration with Claude Desktop

To use the ServiceNow Service Catalog with Claude Desktop:

1. Configure the ServiceNow MCP server in Claude Desktop
2. Ask Claude questions about the service catalog

**Example prompts:**
- "Can you list the available service catalog categories in ServiceNow?"
- "Can you show me the available items in the ServiceNow service catalog?"
- "Can you list the catalog items in the Hardware category?"
- "Can you show me the details of the 'New Laptop' catalog item?"
- "Can you find catalog items related to 'software' in ServiceNow?"
- "Can you create a new category called 'Cloud Services' in the service catalog?"
- "Can you update the 'Hardware' category to rename it to 'IT Equipment'?"
- "Can you move the 'Virtual Machine' catalog item to the 'Cloud Services' category?"
- "Can you create a subcategory called 'Monitors' under the 'IT Equipment' category?"
- "Can you reorganize our catalog by moving all software items to the 'Software' category?"

## Example Scripts

### Integration Test

The `examples/catalog_integration_test.py` script demonstrates how to use the catalog tools directly:

```bash
python examples/catalog_integration_test.py
```

### Claude Desktop Demo

The `examples/claude_catalog_demo.py` script demonstrates how to use the catalog functionality with Claude Desktop:

```bash
python examples/claude_catalog_demo.py
```

## Data Models

### CatalogItemModel

Represents a ServiceNow catalog item.

**Fields:**
- `sys_id` (string): Unique identifier for the catalog item
- `name` (string): Name of the catalog item
- `short_description` (string, optional): Short description of the catalog item
- `description` (string, optional): Detailed description of the catalog item
- `category` (string, optional): Category of the catalog item
- `price` (string, optional): Price of the catalog item
- `picture` (string, optional): Picture URL of the catalog item
- `active` (boolean, optional): Whether the catalog item is active
- `order` (integer, optional): Order of the catalog item in its category

### CatalogCategoryModel

Represents a ServiceNow catalog category.

**Fields:**
- `sys_id` (string): Unique identifier for the category
- `title` (string): Title of the category
- `description` (string, optional): Description of the category
- `parent` (string, optional): Parent category ID
- `icon` (string, optional): Icon of the category
- `active` (boolean, optional): Whether the category is active
- `order` (integer, optional): Order of the category

### CatalogItemVariableModel

Represents a ServiceNow catalog item variable.

**Fields:**
- `sys_id` (string): Unique identifier for the variable
- `name` (string): Name of the variable
- `label` (string): Label of the variable
- `type` (string): Type of the variable
- `mandatory` (boolean, optional): Whether the variable is mandatory
- `default_value` (string, optional): Default value of the variable
- `help_text` (string, optional): Help text for the variable
- `order` (integer, optional): Order of the variable