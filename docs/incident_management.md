# Incident Management

This document describes the incident management functionality provided by the ServiceNow MCP server.

## Overview

The incident management module allows LLMs to interact with ServiceNow incidents through the Model Context Protocol (MCP). It provides resources for querying incident data and tools for creating, updating, and resolving incidents.

## Resources

### List Incidents

Retrieves a list of incidents from ServiceNow.

**Resource Name:** `incidents`

**Parameters:**
- `limit` (int, default: 10): Maximum number of incidents to return
- `offset` (int, default: 0): Offset for pagination
- `state` (string, optional): Filter by incident state
- `assigned_to` (string, optional): Filter by assigned user
- `category` (string, optional): Filter by category
- `query` (string, optional): Search query for incidents

**Example:**
```python
incidents = await mcp.get_resource("servicenow", "incidents", {
    "limit": 5,
    "state": "1",  # New
    "category": "Software"
})

for incident in incidents:
    print(f"{incident.number}: {incident.short_description}")
```

### Get Incident

Retrieves a specific incident from ServiceNow by ID or number.

**Resource Name:** `incident`

**Parameters:**
- `incident_id` (string): Incident ID or sys_id

**Example:**
```python
incident = await mcp.get_resource("servicenow", "incident", "INC0010001")
print(f"Incident: {incident.number}")
print(f"Description: {incident.short_description}")
print(f"State: {incident.state}")
```

## Tools

### Create Incident

Creates a new incident in ServiceNow.

**Tool Name:** `create_incident`

**Parameters:**
- `short_description` (string, required): Short description of the incident
- `description` (string, optional): Detailed description of the incident
- `caller_id` (string, optional): User who reported the incident
- `category` (string, optional): Category of the incident
- `subcategory` (string, optional): Subcategory of the incident
- `priority` (string, optional): Priority of the incident
- `impact` (string, optional): Impact of the incident
- `urgency` (string, optional): Urgency of the incident
- `assigned_to` (string, optional): User assigned to the incident
- `assignment_group` (string, optional): Group assigned to the incident

**Example:**
```python
result = await mcp.use_tool("servicenow", "create_incident", {
    "short_description": "Email service is down",
    "description": "Users are unable to send or receive emails.",
    "category": "Software",
    "priority": "1"
})

print(f"Incident created: {result.incident_number}")
```

### Update Incident

Updates an existing incident in ServiceNow.

**Tool Name:** `update_incident`

**Parameters:**
- `incident_id` (string, required): Incident ID or sys_id
- `short_description` (string, optional): Short description of the incident
- `description` (string, optional): Detailed description of the incident
- `state` (string, optional): State of the incident
- `category` (string, optional): Category of the incident
- `subcategory` (string, optional): Subcategory of the incident
- `priority` (string, optional): Priority of the incident
- `impact` (string, optional): Impact of the incident
- `urgency` (string, optional): Urgency of the incident
- `assigned_to` (string, optional): User assigned to the incident
- `assignment_group` (string, optional): Group assigned to the incident
- `work_notes` (string, optional): Work notes to add to the incident
- `close_notes` (string, optional): Close notes to add to the incident
- `close_code` (string, optional): Close code for the incident

**Example:**
```python
result = await mcp.use_tool("servicenow", "update_incident", {
    "incident_id": "INC0010001",
    "priority": "2",
    "assigned_to": "admin",
    "work_notes": "Investigating the issue."
})

print(f"Incident updated: {result.success}")
```

### Add Comment

Adds a comment to an incident in ServiceNow.

**Tool Name:** `add_comment`

**Parameters:**
- `incident_id` (string, required): Incident ID or sys_id
- `comment` (string, required): Comment to add to the incident
- `is_work_note` (boolean, default: false): Whether the comment is a work note

**Example:**
```python
result = await mcp.use_tool("servicenow", "add_comment", {
    "incident_id": "INC0010001",
    "comment": "The issue is being investigated by the network team.",
    "is_work_note": true
})

print(f"Comment added: {result.success}")
```

### Resolve Incident

Resolves an incident in ServiceNow.

**Tool Name:** `resolve_incident`

**Parameters:**
- `incident_id` (string, required): Incident ID or sys_id
- `resolution_code` (string, required): Resolution code for the incident
- `resolution_notes` (string, required): Resolution notes for the incident

**Example:**
```python
result = await mcp.use_tool("servicenow", "resolve_incident", {
    "incident_id": "INC0010001",
    "resolution_code": "Solved (Permanently)",
    "resolution_notes": "The email service has been restored."
})

print(f"Incident resolved: {result.success}")
```

### Get Incident

Retrieves a specific incident from ServiceNow by ID or number.

**Tool Name:** `get_incident`

**Parameters:**
- `incident_id` (string, required): Incident ID or sys_id to retrieve

**Example:**
```python
result = await mcp.use_tool("servicenow", "get_incident", {
    "incident_id": "INC0010001"
})

if result["success"]:
    incident = result["data"]
    print(f"Incident: {incident['number']}")
    print(f"Description: {incident['short_description']}")
    print(f"State: {incident['state']}")
```

## State Values

ServiceNow incident states are represented by numeric values:

- `1`: New
- `2`: In Progress
- `3`: On Hold
- `4`: Resolved
- `5`: Closed
- `6`: Canceled

## Priority Values

ServiceNow incident priorities are represented by numeric values:

- `1`: Critical
- `2`: High
- `3`: Moderate
- `4`: Low
- `5`: Planning

## Testing

You can test the incident management functionality using the provided test script:

```bash
python examples/test_incidents.py
```

Make sure to set the required environment variables in your `.env` file:

```
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic