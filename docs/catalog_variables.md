# Catalog Item Variables in ServiceNow MCP

This document describes the tools available for managing variables (form fields) in ServiceNow catalog items using the ServiceNow MCP server.

## Overview

Catalog item variables are the form fields that users fill out when ordering items from the service catalog. They collect information needed to fulfill service requests. These tools allow you to create, list, and update variables for catalog items.

## Available Tools

### create_catalog_item_variable

Creates a new variable (form field) for a catalog item.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| catalog_item_id | string | Yes | The sys_id of the catalog item |
| name | string | Yes | The name of the variable (internal name) |
| type | string | Yes | The type of variable (e.g., string, integer, boolean, reference) |
| label | string | Yes | The display label for the variable |
| mandatory | boolean | No | Whether the variable is required (default: false) |
| help_text | string | No | Help text to display with the variable |
| default_value | string | No | Default value for the variable |
| description | string | No | Description of the variable |
| order | integer | No | Display order of the variable |
| reference_table | string | No | For reference fields, the table to reference |
| reference_qualifier | string | No | For reference fields, the query to filter reference options |
| max_length | integer | No | Maximum length for string fields |
| min | integer | No | Minimum value for numeric fields |
| max | integer | No | Maximum value for numeric fields |

#### Example

```python
result = create_catalog_item_variable({
    "catalog_item_id": "item123",
    "name": "requested_for",
    "type": "reference",
    "label": "Requested For",
    "mandatory": true,
    "reference_table": "sys_user",
    "reference_qualifier": "active=true",
    "help_text": "User who needs this item"
})
```

#### Response

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether the operation was successful |
| message | string | A message describing the result |
| variable_id | string | The sys_id of the created variable |
| details | object | Additional details about the variable |

### list_catalog_item_variables

Lists all variables (form fields) for a catalog item.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| catalog_item_id | string | Yes | The sys_id of the catalog item |
| include_details | boolean | No | Whether to include detailed information about each variable (default: true) |
| limit | integer | No | Maximum number of variables to return |
| offset | integer | No | Offset for pagination |

#### Example

```python
result = list_catalog_item_variables({
    "catalog_item_id": "item123",
    "include_details": true,
    "limit": 10,
    "offset": 0
})
```

#### Response

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether the operation was successful |
| message | string | A message describing the result |
| variables | array | List of variables |
| count | integer | Total number of variables found |

### update_catalog_item_variable

Updates an existing variable (form field) for a catalog item.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| variable_id | string | Yes | The sys_id of the variable to update |
| label | string | No | The display label for the variable |
| mandatory | boolean | No | Whether the variable is required |
| help_text | string | No | Help text to display with the variable |
| default_value | string | No | Default value for the variable |
| description | string | No | Description of the variable |
| order | integer | No | Display order of the variable |
| reference_qualifier | string | No | For reference fields, the query to filter reference options |
| max_length | integer | No | Maximum length for string fields |
| min | integer | No | Minimum value for numeric fields |
| max | integer | No | Maximum value for numeric fields |

#### Example

```python
result = update_catalog_item_variable({
    "variable_id": "var123",
    "label": "Updated Label",
    "mandatory": true,
    "help_text": "New help text",
    "order": 200
})
```

#### Response

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether the operation was successful |
| message | string | A message describing the result |
| variable_id | string | The sys_id of the updated variable |
| details | object | Additional details about the variable |

## Common Variable Types

ServiceNow supports various variable types:

| Type | Description |
|------|-------------|
| string | Single-line text field |
| multi_line_text | Multi-line text area |
| integer | Whole number field |
| float | Decimal number field |
| boolean | Checkbox (true/false) |
| choice | Dropdown menu or radio buttons |
| reference | Reference to another record |
| date | Date picker |
| datetime | Date and time picker |
| password | Password field (masked input) |
| email | Email address field |
| url | URL field |
| currency | Currency field |
| html | Rich text editor |
| upload | File attachment |

## Example Usage with Claude

Once the ServiceNow MCP server is configured with Claude, you can ask Claude to perform actions like:

- "Create a description field for the laptop request catalog item"
- "Add a dropdown field for selecting laptop models to catalog item sys_id_123"
- "List all variables for the VPN access request catalog item"
- "Make the department field mandatory in the software request form"
- "Update the help text for the cost center field in the travel request form"
- "Add a reference field to the computer request form that lets users select their manager"
- "Show all variables for the new hire onboarding catalog item in order"
- "Change the order of fields in the hardware request form to put name first"

## Troubleshooting

### Common Errors

1. **Error: `Mandatory variable not provided`**
   - This error occurs when you don't provide all required parameters when creating a variable.
   - Solution: Make sure to include all required parameters: `catalog_item_id`, `name`, `type`, and `label`.

2. **Error: `Invalid variable type specified`**
   - This error occurs when you provide an invalid value for the `type` parameter.
   - Solution: Use one of the valid variable types listed in the "Common Variable Types" section.

3. **Error: `Reference table required for reference variables`**
   - This error occurs when creating a reference-type variable without specifying the `reference_table`.
   - Solution: Always include the `reference_table` parameter when creating reference-type variables.

4. **Error: `No update parameters provided`**
   - This error occurs when calling `update_catalog_item_variable` with only the variable_id and no other parameters.
   - Solution: Provide at least one field to update. 