# Incident Management

This document describes the incident management functionality provided by the ServiceNow MCP server.

## Overview

The incident management module allows LLMs to interact with ServiceNow incidents through the Model Context Protocol (MCP). It provides tools for the full incident lifecycle: creating, reading (by number or sys_id), listing/searching, updating, commenting, resolving, and deleting incidents.

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
- `urgency` (string, optional): Filter by urgency (`1` High, `2` Medium, `3` Low)
- `severity` (string, optional): Filter by severity (`1` High, `2` Medium, `3` Low)
- `impact` (string, optional): Filter by impact (`1` High, `2` Medium, `3` Low)
- `priority` (string, optional): Filter by priority (`1` Critical … `5` Planning)
- `query` (string, optional): Free-text keyword search across short description / description
- `created_after` (string, optional): Only incidents created **on/after** this date (`YYYY-MM-DD` = start of day, or `YYYY-MM-DD HH:MM:SS`)
- `created_before` (string, optional): Only incidents created **on/before** this date (`YYYY-MM-DD` = end of day, or `YYYY-MM-DD HH:MM:SS`)
- `updated_after` (string, optional): Only incidents whose **last update/response** was on/after this date
- `updated_before` (string, optional): Only incidents whose **last update/response** was on/before this date

Results are ordered newest-first by creation date. Combine `created_after` +
`created_before` for a "between two dates" search; date and free-text filters can
be combined freely.

**Examples:**
```python
# Incidents created on a specific day
list_incidents({"created_after": "2026-06-19", "created_before": "2026-06-19"})

# Incidents created between two dates
list_incidents({"created_after": "2026-06-01", "created_before": "2026-06-30"})

# Incidents whose last response was in the last week (open + recently touched)
list_incidents({"state": "2", "updated_after": "2026-06-12"})

# Free-text + date range together
list_incidents({"query": "VPN", "created_after": "2026-06-01", "limit": 50})

# High-urgency, high-severity open incidents
list_incidents({"urgency": "1", "severity": "1", "state": "2"})

# Keyword search (short description / description)
list_incidents({"query": "password reset"})
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
- `caller_id` (string, optional): Caller — accepts a sys_id, username, full name, or email
- `channel` (string, optional): Channel / contact type — `email`, `phone`, `chat`, `self-service`, `walk-in`, `virtual_agent`
- `category` (string, optional): Category of the incident
- `subcategory` (string, optional): Subcategory of the incident
- `priority` (string, optional): Priority — usually **auto-calculated** from `impact` × `urgency`, so prefer setting those
- `impact` (string, optional): Impact (`1` High, `2` Medium, `3` Low)
- `urgency` (string, optional): Urgency (`1` High, `2` Medium, `3` Low)
- `assigned_to` (string, optional): Assignee — accepts a sys_id, username, full name, or email
- `assignment_group` (string, optional): Assignment group — accepts a sys_id or group name

> **Reference fields** (`caller_id`, `assigned_to`, `assignment_group`) accept a
> human name and are resolved to a sys_id automatically. **Priority** is derived
> from impact × urgency by ServiceNow; setting it directly is usually overridden.
> Note: some instances enforce that an `assigned_to` user belongs to the
> `assignment_group` when both are set in the same update.

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
- `incident_id` (string, required): Incident number or sys_id
- `short_description` (string, optional): Short description of the incident
- `description` (string, optional): Detailed description of the incident
- `state` (string, optional): State code (`1` New, `2` In Progress, `3` On Hold, `6` Resolved, `7` Closed, `8` Canceled)
- `channel` (string, optional): Channel / contact type (`email`, `phone`, `chat`, `self-service`, `walk-in`)
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
- `incident_id` (string, required): Incident number or sys_id
- `resolution_code` (string, required): Resolution code — **must be one of the instance's configured "Resolution code" choices**
- `resolution_notes` (string, required): Resolution notes for the incident

This tool sets `state=6`, `close_code`, and `close_notes`. It does **not** send
`resolved_at` — ServiceNow populates `resolved_at`/`resolved_by` automatically.

> **Valid `resolution_code` values are instance-specific.** On a default
> Personal Developer Instance they include: `Solution provided`,
> `Workaround provided`, `Resolved by caller`, `Resolved by change`,
> `Resolved by problem`, `Resolved by request`, `Known error`, `Duplicate`,
> `User error`, `No resolution provided`. Sending a value that is not a
> configured choice is silently dropped, which then trips the mandatory-field
> Data Policy and the resolve fails with HTTP 403. To list the valid choices for
> your instance, query `sys_choice` for `name=incident^element=close_code`.

**Example:**
```python
result = await mcp.use_tool("servicenow", "resolve_incident", {
    "incident_id": "INC0010001",
    "resolution_code": "Solution provided",
    "resolution_notes": "The email service has been restored."
})

print(f"Incident resolved: {result.success}")
```

### Get Incident

Retrieves a single incident by **number or sys_id**.

**Tool Name:** `get_incident`

**Parameters:**
- `incident_id` (string, required): Incident number (e.g. `INC0010001`) or sys_id

**Example:**
```python
result = await mcp.use_tool("servicenow", "get_incident", {"incident_id": "INC0010001"})
print(result["incident"]["state"])
```

### Close Incident

Closes an incident (state = `7` Closed). Like resolving, the resolution code and
close notes are mandatory.

**Tool Name:** `close_incident`

**Parameters:**
- `incident_id` (string, required): Incident number or sys_id
- `close_code` (string, required): Resolution code (instance-specific choice — see Resolve Incident)
- `close_notes` (string, required): Close notes

### Reopen Incident

Reopens a resolved/closed incident (state = `2` In Progress).

**Tool Name:** `reopen_incident`

**Parameters:**
- `incident_id` (string, required): Incident number or sys_id
- `reopen_notes` (string, optional): Work note explaining why it is being reopened

### Delete Incident

Deletes an incident by **number or sys_id**. *(Destructive — requires a role
with delete access on the incident table.)*

**Tool Name:** `delete_incident`

**Parameters:**
- `incident_id` (string, required): Incident number (e.g. `INC0010001`) or sys_id

**Example:**
```python
result = await mcp.use_tool("servicenow", "delete_incident", {"incident_id": "INC0010001"})
print(f"Deleted: {result.success}")
```

## Read output: codes vs. labels

The read tools (`list_incidents`, `get_incident`, `get_incident_by_number`)
return coded fields as **both** the raw code and a display label:

- `state` → the code (e.g. `"6"`), with `state_display` → `"Resolved"`
- `priority` → the code (e.g. `"3"`), with `priority_display` → `"3 - Moderate"`

Pass the **code** (`state`, `priority`) back into `update_incident` and into
`list_incidents` filters; use the `*_display` values for presentation.

## State Values

ServiceNow incident states are represented by numeric values. Pass these codes
(not the display labels) as the `state` parameter to `update_incident`:

- `1`: New
- `2`: In Progress
- `3`: On Hold
- `6`: Resolved
- `7`: Closed
- `8`: Canceled

> **Note:** Moving an incident to `6` (Resolved) or `7` (Closed) is gated by a
> ServiceNow Data Policy that makes **Resolution code (`close_code`)** and
> **Close notes (`close_notes`)** mandatory. Use `resolve_incident` (which sets
> them) rather than `update_incident` with `state=6` alone — otherwise the
> instance rejects the change with an HTTP 403 *"Data Policy Exception: the
> following fields are mandatory"*. Moving to `3` (On Hold) may require
> `on_hold_reason` depending on the instance.

## Priority Values

ServiceNow incident priorities are represented by numeric values:

- `1`: Critical
- `2`: High
- `3`: Moderate
- `4`: Low
- `5`: Planning

## Testing

You can exercise **every** incident tool end-to-end against a live instance with
the provided script. It drives the real tool functions and re-fetches each record
after every change to confirm the change actually persisted (a tool can return
HTTP 200 while ServiceNow silently ignores an invalid field value):

```bash
.venv/Scripts/python scripts/test_incidents_live.py          # create..resolve..delete
.venv/Scripts/python scripts/test_incidents_live.py --keep   # leave the test incident in place
```

Make sure to set the required environment variables in your `.env` file:

```
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
SERVICENOW_AUTH_TYPE=basic
``` 