# Task Management

This document describes the task management functionality provided by the ServiceNow MCP server.

## Overview

The task management module allows LLMs to interact with ServiceNow tasks through the Model Context Protocol (MCP). It provides resources for querying task data and tools for creating, updating, and completing tasks.

## Resources

### List Tasks

Retrieves a list of tasks from ServiceNow.

**Resource Name:** `tasks`

**Parameters:**
- `limit` (int, default: 10): Maximum number of tasks to return
- `offset` (int, default: 0): Offset for pagination
- `state` (string, optional): Filter by task state
- `assigned_to` (string, optional): Filter by assigned user
- `category` (string, optional): Filter by category
- `query` (string, optional): Search query for tasks

**Example:**
```python
tasks = await mcp.get_resource("servicenow", "tasks", {
    "limit": 5,
    "state": "1",  # Open
    "category": "Software"
})

for task in tasks:
    print(f"{task.number}: {task.short_description}")
```

### Get Task

Retrieves a specific task from ServiceNow by number.

**Resource Name:** `task`

**Parameters:**
- `task_id` (string): Task number or sys_id

**Example:**
```python
task = await mcp.get_resource("servicenow", "task", "TASK0010001")
print(f"Task: {task.number}")
print(f"Description: {task.short_description}")
print(f"State: {task.state}")
```

## Tools

### Create Task

Creates a new task in ServiceNow.

**Tool Name:** `create_task`

**Parameters:**
- `short_description` (string, required): Short description of the task
- `description` (string, optional): Detailed description of the task
- `caller_id` (string, optional): User who reported the task
- `category` (string, optional): Category of the task
- `priority` (string, optional): Priority of the task
- `due_date` (string, optional): Due date for the task
- `assigned_to` (string, optional): User assigned to the task
- `assignment_group` (string, optional): Group assigned to the task

**Example:**
```python
result = await mcp.use_tool("servicenow", "create_task", {
    "short_description": "Configure new server",
    "description": "Install and configure software on the new accounting server.",
    "category": "Infrastructure",
    "priority": "3"
})

print(f"Task created: {result.task_number}")
```

### Update Task

Updates an existing task in ServiceNow.

**Tool Name:** `update_task`

**Parameters:**
- `task_id` (string, required): Task ID or sys_id
- `short_description` (string, optional): Short description of the task
- `description` (string, optional): Detailed description of the task
- `state` (string, optional): State of the task
- `category` (string, optional): Category of the task
- `priority` (string, optional): Priority of the task
- `due_date` (string, optional): Due date for the task
- `assigned_to` (string, optional): User assigned to the task
- `assignment_group` (string, optional): Group assigned to the task
- `work_notes` (string, optional): Work notes to add to the task

**Example:**
```python
result = await mcp.use_tool("servicenow", "update_task", {
    "task_id": "TASK0010001",
    "priority": "2",
    "assigned_to": "admin",
    "work_notes": "Increasing priority due to deadline change."
})

print(f"Task updated: {result.success}")
```

### Add Task Comment

Adds a comment to a task in ServiceNow.

**Tool Name:** `add_task_comment`

**Parameters:**
- `task_id` (string, required): Task ID or sys_id
- `comment` (string, required): Comment to add to the task
- `is_work_note` (boolean, default: false): Whether the comment is a work note

**Example:**
```python
result = await mcp.use_tool("servicenow", "add_task_comment", {
    "task_id": "TASK0010001",
    "comment": "Progress update: 50% complete.",
    "is_work_note": true
})

print(f"Comment added: {result.success}")
```

### Complete Task

Completes a task in ServiceNow.

**Tool Name:** `complete_task`

**Parameters:**
- `task_id` (string, required): Task ID or sys_id
- `close_notes` (string, required): Notes about task completion
- `close_code` (string, optional): Close code for the task

**Example:**
```python
result = await mcp.use_tool("servicenow", "complete_task", {
    "task_id": "TASK0010001",
    "close_notes": "Task completed successfully. All software installed and configured."
})

print(f"Task completed: {result.success}")
```

### List Tasks

Lists tasks from ServiceNow with filtering options.

**Tool Name:** `list_tasks`

**Parameters:**
- `limit` (int, default: 10): Maximum number of tasks to return
- `offset` (int, default: 0): Offset for pagination
- `state` (string, optional): Filter by task state
- `assigned_to` (string, optional): Filter by assigned user
- `category` (string, optional): Filter by category
- `query` (string, optional): Search query for tasks

**Example:**
```python
result = await mcp.use_tool("servicenow", "list_tasks", {
    "limit": 5,
    "state": "1",  # Open
    "category": "Infrastructure"
})

print(f"Found {len(result['tasks'])} tasks")
```

### Get Task

Retrieves a specific task from ServiceNow by its number.

**Tool Name:** `get_task`

**Parameters:**
- `task_number` (string, required): Task number to retrieve

**Example:**
```python
result = await mcp.use_tool("servicenow", "get_task", {
    "task_number": "TASK0010001"
})

if result["success"]:
    task = result["data"]
    print(f"Task: {task['number']}")
    print(f"Description: {task['short_description']}")
    print(f"State: {task['state']}")
```

## State Values

ServiceNow task states are typically represented by numeric values:

- `1`: Open
- `2`: Work in Progress
- `3`: Closed Complete
- `4`: Closed Incomplete
- `7`: Closed Skipped

## Priority Values

ServiceNow task priorities are represented by numeric values:

- `1`: Critical
- `2`: High
- `3`: Moderate
- `4`: Low
- `5`: Planning

## Testing

You can test the task management functionality using the provided test script:

```bash
python examples/test_tasks.py
```

Make sure to set the required environment variables in your `.env` file:

```
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic
```
