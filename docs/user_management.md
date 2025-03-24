# User Management in ServiceNow MCP

This document provides detailed information about the User Management tools available in the ServiceNow MCP server.

## Overview

The User Management tools allow you to create, update, and manage users and groups in ServiceNow. These tools are essential for setting up test environments, creating users with specific roles, and organizing users into assignment groups.

## Available Tools

### User Management

1. **create_user** - Create a new user in ServiceNow
2. **update_user** - Update an existing user in ServiceNow
3. **get_user** - Get a specific user by ID, username, or email
4. **list_users** - List users with filtering options

### Group Management

5. **create_group** - Create a new group in ServiceNow
6. **update_group** - Update an existing group in ServiceNow
7. **add_group_members** - Add members to a group in ServiceNow
8. **remove_group_members** - Remove members from a group in ServiceNow

## Tool Details

### create_user

Creates a new user in ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_name | string | Yes | Username for the user |
| first_name | string | Yes | First name of the user |
| last_name | string | Yes | Last name of the user |
| email | string | Yes | Email address of the user |
| title | string | No | Job title of the user |
| department | string | No | Department the user belongs to |
| manager | string | No | Manager of the user (sys_id or username) |
| roles | array | No | Roles to assign to the user |
| phone | string | No | Phone number of the user |
| mobile_phone | string | No | Mobile phone number of the user |
| location | string | No | Location of the user |
| password | string | No | Password for the user account |
| active | boolean | No | Whether the user account is active (default: true) |

#### Example

```python
# Create a new user in the Radiology department
result = create_user({
    "user_name": "alice.radiology",
    "first_name": "Alice",
    "last_name": "Radiology",
    "email": "alice@example.com",
    "title": "Doctor",
    "department": "Radiology",
    "roles": ["user"]
})
```

### update_user

Updates an existing user in ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID or sys_id to update |
| user_name | string | No | Username for the user |
| first_name | string | No | First name of the user |
| last_name | string | No | Last name of the user |
| email | string | No | Email address of the user |
| title | string | No | Job title of the user |
| department | string | No | Department the user belongs to |
| manager | string | No | Manager of the user (sys_id or username) |
| roles | array | No | Roles to assign to the user |
| phone | string | No | Phone number of the user |
| mobile_phone | string | No | Mobile phone number of the user |
| location | string | No | Location of the user |
| password | string | No | Password for the user account |
| active | boolean | No | Whether the user account is active |

#### Example

```python
# Update a user to set their manager
result = update_user({
    "user_id": "user123",
    "manager": "user456",
    "title": "Senior Doctor"
})
```

### get_user

Gets a specific user from ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | No | User ID or sys_id |
| user_name | string | No | Username of the user |
| email | string | No | Email address of the user |

**Note**: At least one of the parameters must be provided.

#### Example

```python
# Get a user by username
result = get_user({
    "user_name": "alice.radiology"
})
```

### list_users

Lists users from ServiceNow with filtering options.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Maximum number of users to return (default: 10) |
| offset | integer | No | Offset for pagination (default: 0) |
| active | boolean | No | Filter by active status |
| department | string | No | Filter by department |
| query | string | No | Search query for users |

#### Example

```python
# List users in the Radiology department
result = list_users({
    "department": "Radiology",
    "active": true,
    "limit": 20
})
```

### create_group

Creates a new group in ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Name of the group |
| description | string | No | Description of the group |
| manager | string | No | Manager of the group (sys_id or username) |
| parent | string | No | Parent group (sys_id or name) |
| type | string | No | Type of the group |
| email | string | No | Email address for the group |
| members | array | No | List of user sys_ids or usernames to add as members |
| active | boolean | No | Whether the group is active (default: true) |

#### Example

```python
# Create a new group for Biomedical Engineering
result = create_group({
    "name": "Biomedical Engineering",
    "description": "Group for biomedical engineering staff",
    "manager": "user456",
    "members": ["admin", "alice.radiology"]
})
```

### update_group

Updates an existing group in ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| group_id | string | Yes | Group ID or sys_id to update |
| name | string | No | Name of the group |
| description | string | No | Description of the group |
| manager | string | No | Manager of the group (sys_id or username) |
| parent | string | No | Parent group (sys_id or name) |
| type | string | No | Type of the group |
| email | string | No | Email address for the group |
| active | boolean | No | Whether the group is active |

#### Example

```python
# Update a group to change its manager
result = update_group({
    "group_id": "group123",
    "description": "Updated description for biomedical engineering group",
    "manager": "user789"
})
```

### add_group_members

Adds members to a group in ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| group_id | string | Yes | Group ID or sys_id |
| members | array | Yes | List of user sys_ids or usernames to add as members |

#### Example

```python
# Add members to the Biomedical Engineering group
result = add_group_members({
    "group_id": "group123",
    "members": ["bob.chiefradiology", "admin"]
})
```

### remove_group_members

Removes members from a group in ServiceNow.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| group_id | string | Yes | Group ID or sys_id |
| members | array | Yes | List of user sys_ids or usernames to remove as members |

#### Example

```python
# Remove a member from the Biomedical Engineering group
result = remove_group_members({
    "group_id": "group123",
    "members": ["alice.radiology"]
})
```

## Common Scenarios

### Creating Test Users and Groups for Approval Workflows

To set up test users and groups for an approval workflow:

1. Create department head user:

```python
bob_result = create_user({
    "user_name": "bob.chiefradiology",
    "first_name": "Bob",
    "last_name": "ChiefRadiology",
    "email": "bob@example.com",
    "title": "Chief of Radiology",
    "department": "Radiology",
    "roles": ["itil", "admin"]  # assign ITIL role for approvals
})
```

2. Create staff user with department head as manager:

```python
alice_result = create_user({
    "user_name": "alice.radiology",
    "first_name": "Alice",
    "last_name": "Radiology",
    "email": "alice@example.com",
    "title": "Doctor",
    "department": "Radiology",
    "manager": bob_result.user_id  # Set Bob as Alice's manager
})
```

3. Create assignment group for fulfillment:

```python
group_result = create_group({
    "name": "Biomedical Engineering",
    "description": "Group for biomedical engineering staff",
    "members": ["admin"]  # Add administrator as a member
})
```

### Finding Users in a Department

To find all users in a specific department:

```python
users = list_users({
    "department": "Radiology",
    "limit": 50
})
```

### Setting up Role-Based Access Control

To assign specific roles to users:

```python
# Assign ITIL role to a user so they can approve changes
update_user({
    "user_id": "user123",
    "roles": ["itil"]
})
```

## Troubleshooting

### Common Errors

1. **User already exists**
   - This error occurs when trying to create a user with a username that already exists
   - Solution: Use a different username or update the existing user instead

2. **User not found**
   - This error occurs when trying to update, get, or add a user that doesn't exist
   - Solution: Verify the user ID, username, or email is correct

3. **Role not found**
   - This error occurs when trying to assign a role that doesn't exist
   - Solution: Check the role name and make sure it exists in the ServiceNow instance

4. **Group not found**
   - This error occurs when trying to update or add members to a group that doesn't exist
   - Solution: Verify the group ID is correct

## Best Practices

1. **Use meaningful usernames**: Create usernames that reflect the user's identity, such as "firstname.lastname"

2. **Set up proper role assignments**: Only assign the necessary roles to users to maintain security best practices

3. **Organize users into appropriate groups**: Use groups to organize users based on departments, functions, or teams

4. **Manage group memberships carefully**: Add or remove users from groups to ensure proper assignment and notification routing

5. **Set managers for hierarchical approval flows**: When creating users that will be part of approval workflows, make sure to set the manager field appropriately 