# Workflow Management in ServiceNow MCP

This document provides detailed information about the workflow management tools available in the ServiceNow MCP server.

## Overview

ServiceNow workflows are a powerful automation feature that allows you to define and automate business processes. The workflow management tools in the ServiceNow MCP server enable you to view, create, and modify workflows in your ServiceNow instance.

> **Note:** These tools target the **legacy** workflow engine (`wf_workflow` /
> `wf_workflow_version` / `wf_activity`). Modern instances use Flow Designer, so
> the legacy engine is often empty. CRUD on workflows works (create, get, update,
> `delete_workflow`, list); a workflow's `active` flag and its activities are
> governed by whether a version is published, so `activate_workflow` /
> `get_workflow_activities` reflect that state rather than forcing it.

## Available Tools

### Viewing Workflows

1. **list_workflows** - List workflows from ServiceNow
   - Parameters:
     - `limit` (optional): Maximum number of records to return (default: 10)
     - `offset` (optional): Offset to start from (default: 0)
     - `active` (optional): Filter by active status (true/false)
     - `name` (optional): Filter by name (contains)
     - `query` (optional): Additional query string

2. **get_workflow_details** - Get detailed information about a specific workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id

3. **list_workflow_versions** - List all versions of a specific workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id
     - `limit` (optional): Maximum number of records to return (default: 10)
     - `offset` (optional): Offset to start from (default: 0)

4. **get_workflow_activities** - Get all activities in a workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id
     - `version` (optional): Specific version to get activities for (if not provided, the latest published version will be used)

### Modifying Workflows

5. **create_workflow** - Create a new workflow in ServiceNow
   - Parameters:
     - `name` (required): Name of the workflow
     - `description` (optional): Description of the workflow
     - `table` (optional): Table the workflow applies to
     - `active` (optional): Whether the workflow is active (default: true)
     - `attributes` (optional): Additional attributes for the workflow

6. **update_workflow** - Update an existing workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id
     - `name` (optional): Name of the workflow
     - `description` (optional): Description of the workflow
     - `table` (optional): Table the workflow applies to
     - `active` (optional): Whether the workflow is active
     - `attributes` (optional): Additional attributes for the workflow

7. **activate_workflow** - Activate a workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id

8. **deactivate_workflow** - Deactivate a workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id

### Managing Workflow Activities

9. **add_workflow_activity** - Add a new activity to a workflow
   - Parameters:
     - `workflow_id` (required): Workflow ID or sys_id
     - `name` (required): Name of the activity
     - `description` (optional): Description of the activity
     - `activity_type` (required): Type of activity (e.g., 'approval', 'task', 'notification')
     - `attributes` (optional): Additional attributes for the activity
     - `position` (optional): Position in the workflow (if not provided, the activity will be added at the end)

10. **update_workflow_activity** - Update an existing activity in a workflow
    - Parameters:
      - `activity_id` (required): Activity ID or sys_id
      - `name` (optional): Name of the activity
      - `description` (optional): Description of the activity
      - `attributes` (optional): Additional attributes for the activity

11. **delete_workflow_activity** - Delete an activity from a workflow
    - Parameters:
      - `activity_id` (required): Activity ID or sys_id

12. **reorder_workflow_activities** - Change the order of activities in a workflow
    - Parameters:
      - `workflow_id` (required): Workflow ID or sys_id
      - `activity_ids` (required): List of activity IDs in the desired order

## Usage Examples

### Viewing Workflows

#### List all active workflows

```python
result = list_workflows({
    "active": True,
    "limit": 20
})
```

#### Get details about a specific workflow

```python
result = get_workflow_details({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590"
})
```

#### List all versions of a workflow

```python
result = list_workflow_versions({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590"
})
```

#### Get all activities in a workflow

```python
result = get_workflow_activities({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590"
})
```

### Modifying Workflows

#### Create a new workflow

```python
result = create_workflow({
    "name": "Software License Request",
    "description": "Workflow for handling software license requests",
    "table": "sc_request"
})
```

#### Update an existing workflow

```python
result = update_workflow({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590",
    "description": "Updated workflow description",
    "active": True
})
```

#### Activate a workflow

```python
result = activate_workflow({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590"
})
```

#### Deactivate a workflow

```python
result = deactivate_workflow({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590"
})
```

### Managing Workflow Activities

#### Add a new activity to a workflow

```python
result = add_workflow_activity({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590",
    "name": "Manager Approval",
    "description": "Approval step for the manager",
    "activity_type": "approval"
})
```

#### Update an existing activity

```python
result = update_workflow_activity({
    "activity_id": "3cda7cda87a9c150e0b0df23cebb3591",
    "name": "Updated Activity Name",
    "description": "Updated activity description"
})
```

#### Delete an activity

```python
result = delete_workflow_activity({
    "activity_id": "3cda7cda87a9c150e0b0df23cebb3591"
})
```

#### Reorder activities in a workflow

```python
result = reorder_workflow_activities({
    "workflow_id": "2bda7cda87a9c150e0b0df23cebb3590",
    "activity_ids": [
        "3cda7cda87a9c150e0b0df23cebb3591",
        "4cda7cda87a9c150e0b0df23cebb3592",
        "5cda7cda87a9c150e0b0df23cebb3593"
    ]
})
```

## Common Activity Types

ServiceNow provides several activity types that can be used when adding activities to a workflow:

1. **approval** - An approval activity that requires user action
2. **task** - A task that needs to be completed
3. **notification** - Sends a notification to users
4. **timer** - Waits for a specified amount of time
5. **condition** - Evaluates a condition and branches the workflow
6. **script** - Executes a script
7. **wait_for_condition** - Waits until a condition is met
8. **end** - Ends the workflow

## Best Practices

1. **Version Control**: Always create a new version of a workflow before making significant changes.
2. **Testing**: Test workflows in a non-production environment before deploying to production.
3. **Documentation**: Document the purpose and behavior of each workflow and activity.
4. **Error Handling**: Include error handling in your workflows to handle unexpected situations.
5. **Notifications**: Use notification activities to keep stakeholders informed about the workflow progress.

## Troubleshooting

### Common Issues

1. **Error: "No published versions found for this workflow"**
   - This error occurs when trying to get activities for a workflow that has no published versions.
   - Solution: Publish a version of the workflow before trying to get its activities.

2. **Error: "Activity type is required"**
   - This error occurs when trying to add an activity without specifying its type.
   - Solution: Provide a valid activity type when adding an activity.

3. **Error: "Cannot modify a published workflow version"**
   - This error occurs when trying to modify a published workflow version.
   - Solution: Create a new draft version of the workflow before making changes.

4. **Error: "Workflow ID is required"**
   - This error occurs when not providing a workflow ID for operations that require it.
   - Solution: Make sure to include the workflow ID in your request.

## Additional Resources

- [ServiceNow Workflow Documentation](https://docs.servicenow.com/bundle/tokyo-platform-administration/page/administer/workflow-administration/concept/c_WorkflowAdministration.html)
- [ServiceNow Workflow API Reference](https://developer.servicenow.com/dev.do#!/reference/api/tokyo/rest/c_WorkflowAPI) 